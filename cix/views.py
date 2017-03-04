from cix.forms import LoginForm, SignupForm
from cix.logic import get_login_render_page, send_verification_email
from profiles.models import UserProfile
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group, User
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template import RequestContext


def render_with_request_context(request, page, context):
    #return render(page, RequestContext(request, context))
    return render(request, page, context)


def home(request):
    #return render_with_request_context(request, 'home.html', { })
    return HttpResponseRedirect('/ncaa/')


def login_page(request):
    return render_with_request_context(request, 'login.html', { })


def do_login(request):
    if request.user.is_authenticated() or request.method != 'POST':
        return HttpResponseRedirect('/')
    error = ''
    form = LoginForm(request.POST)
    if form.is_valid():
        data = form.cleaned_data
        user = authenticate(username=data['username'], password=data['password'])
        if user:
            #if not user.has_perm('auth.can_login'):
            #    error = 'User is not verified'
            #el
            if not user.is_active:
                error = 'Your account has been disabled.  Please contact site administrators.'
            else:
                login(request, user)
        else:
            error = 'Invalid username or password'
    else:
        error = 'Please enter a valid username and password'

    redirect_target = request.POST.get('redirect_target', '')
    if error:
        return render_with_request_context(request, get_login_render_page(redirect_target), { 'login_error':error })
    #return HttpResponseRedirect(get_login_redirect(request.POST.get(redirect_target)))
    return HttpResponseRedirect(request.POST.get(redirect_target, '/'))

def signup(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect('/')
    return render_with_request_context(request, 'signup.html', { 'form':SignupForm() })


def do_signup(request):
    if request.user.is_authenticated() or request.method != 'POST':
        return HttpResponseRedirect('/')
    form = SignupForm(request.POST)
    if not form.is_valid():
        return render_with_request_context(request, 'signup.html', { 'form':form })
    data = form.cleaned_data
    user = User.objects.create_user(data['username'], data['email'], data['password'])
    #profile = UserProfile.objects.get(user=user)
    #send_verification_email(user.email, profile.verification_id)

    #return HttpResponseRedirect('/signup_thanks/')
    user = authenticate(username=data['username'], password=data['password'])
    login(request, user)
    return HttpResponseRedirect('/ncaa/')


def signup_thanks(request):
    return render_with_request_context(request, 'signup_thanks.html', { })


def do_logout(request):
    if request.user.is_authenticated():
        logout(request)
    return HttpResponseRedirect('/')


def verify(request, verify_id):
    error = ''
    try:
        profile = UserProfile.objects.get(verification_id__exact=verify_id)
    except UserProfile.DoesNotExist:
        error = 'Invalid verification id'
    else:
        if 'Verified' in profile.user.groups.all():
            error = 'User already verified'
        else:
            profile.user.groups.add(Group.objects.get(name='Verified'))
            profile.user.save()
            profile.is_verified = True
            profile.save()
    return render_with_request_context(request, 'verify.html', { 'error':error, 'username':profile.user.username })
