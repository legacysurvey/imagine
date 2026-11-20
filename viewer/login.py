from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required

def login(req):
    from viewer import settings
    from social_core.backends.utils import load_backends
    print('viewer login()')
    ctxt = {}
    ctxt.update({
        'available_backends': load_backends(settings.AUTHENTICATION_BACKENDS)
    })
    return render(req, 'login.html', ctxt)

def logout(request):
    """Logs out user"""
    from django.contrib.auth import logout as auth_logout
    auth_logout(request)
    return redirect('/login')

@login_required
def loggedin(req):
    print('logged in.')
    print('req:', req)
    user = req.user
    print('User:', user)
    print('User type:', type(user))
    if user is None:
        return HttpResponse('Unknown user')
    if not user.is_authenticated:
        return HttpResponse('not authenticated: ' + user)
    if not user.is_active:
        return HttpResponse('User account deactivated')
    return redirect('/')

# @login_required
# def signedin(req):
#     print('signedin.')
#     user = req.user
#     if not user.is_authenticated:
#         return HttpResponse('not authenticated: ' + user)
# 
#     if user is not None:
#         if user.is_active:
#             try:
#                 profile = user.profile
#             except UserProfile.DoesNotExist:
#                 loginfo('Creating new UserProfile for', user)
#                 profile = UserProfile(user=user)
#                 profile.create_api_key()
#                 profile.create_default_license()
#                 if user.get_full_name():
#                     profile.display_name = user.get_full_name()
#                 else:
#                     profile.display_name = user.username
#                 profile.save()
#             return redirect('/')
#         else:
#             return HttpResponse('Disabled account')
#     else:
#         return HttpResponse('Unknown user')
