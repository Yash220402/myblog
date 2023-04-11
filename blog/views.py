from django.shortcuts import render,get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView
from django.contrib.postgres.search import TrigramSimilarity, SearchVector, SearchQuery, SearchRank

from .models import Post, Comment
from .forms import EmailPostForm, CommentForm, SearchForm
from taggit.models import Tag

from django.db.models import Count

# Create your views here.
# def post_list(request):
#     posts = Post.published.all()
#     return render(request,'blog/post/list.html',{'posts': posts})

def post_detail(request, year, month, day, post):
    post = get_object_or_404(Post, slug=post,
                                   status='published',
                                   publish__year=year,
                                   publish__month=month,
                                   publish__day=day)

    # List of active comments for this post
    comments = post.comments.filter(active=True)
    new_comment = None

    if request.method == 'POST':
        # A comment was posted
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            # create comment object but don't save to db yet
            new_comment = comment_form.save(commit=False)
            # assign the current post to the comment
            new_comment.post = post
            # save the comment to the db 
            new_comment.save()
    else:
        comment_form = CommentForm()
    
    # List similar posts
    post_tags_ids = post.tags.values_list('id', flat=True)
    similar_posts = Post.published.filter(tags__in=post_tags_ids).exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count('tags')).order_by('-same_tags', '-publish')[:4]
    
    return render(request, 'blog/post/detail.html', 
                            {'post': post,
                             'comments': comments,
                             'new_comment': new_comment,
                             'comment_form': comment_form,
                             'similar_posts': similar_posts})

def post_list(request, tag_slug=None):
    object_list = Post.published.all()
    tag = None 
    
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        object_list = object_list.filter(tags__in=[tag])


    paginator = Paginator(object_list, 3) # 3 posts in each page
    page = request.GET.get('page')
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        # if page is not an integer deliver the first page
        posts = paginator.page(1)
    except EmptyPage:
        # if page is out of range then deliver the last page
        posts = paginator.page(paginator.num_pages)
    
    return render(request,
                  'blog/post/list.html',
                  {'page': page,
                   'posts': posts,
                   'tag': tag})

# class PostListView(ListView):
#     queryset = Post.published.all()
#     context_object_name = 'posts'
#     paginate_by = 3
#     template_name = 'blog/post/list.html'


from django.core.mail import send_mail
def post_share(request, post_id):
    # Retrieve post by id
    post = get_object_or_404(Post, id=post_id, status='published')
    sent = False
    
    if request.method == 'POST':
        # form was submitted
        form = EmailPostForm(request.POST)
        if form.is_valid():
            # form fields passed validation
            cd = form.cleaned_data
            # ... send data
            post_url = request.build_absolute_url(post.get_absolute_url())
            subject = f"{cd['name']} recommends you read " f"{post.title}"
            message = f"Read {post.title} at {post_url}\n\n{cd['name']}'s comments: {cd['comments']}"
            send_mail(subject, message, 'aztec220402@gmail.com', [cd['to']])
    else:
        form = EmailPostForm()
    return render(request, 'blog/post/share.html', {'post': post, 'form': form})

def post_search(request):
    form = SearchForm()
    query = None 
    results = [] 

    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            search_vector = SearchVector('title', weight='A') + SearchVector('body', weight='B')
            search_query = SearchQuery(query)
            results = Post.published.annotate(
                        similarity=TrigramSimilarity('title', query) + TrigramSimilarity('body', query)
                    ).filter(similarity__gt=0.1).order_by('-similarity')
    
    return render(request,
                'blog/post/search.html',
                {'form': form,
                'query': query,
                'results': results})