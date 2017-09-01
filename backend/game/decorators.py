from functools import wraps

from django.conf import settings
from django.contrib.auth import SESSION_KEY
from django.contrib.auth import authenticate
from django.contrib.auth import get_user
from django.contrib.auth import login
from django.shortcuts import redirect
from django.utils.decorators import available_attrs

from lazysignup.constants import USER_AGENT_BLACKLIST
from lazysignup.utils import is_lazy_user

ALLOW_LAZY_REGISTRY = {}


def allow_lazy_user_view_set(func):
    def wrapped(viewset, *args, **kwargs):
        request = viewset.request
        assert hasattr(request, 'session'), ("You need to have the session "
                                             "app intsalled")
        if getattr(settings, 'LAZYSIGNUP_ENABLE', True):
            # If the user agent is one we ignore, bail early
            ignore = False
            request_user_agent = request.META.get('HTTP_USER_AGENT', '')
            for user_agent in USER_AGENT_BLACKLIST:
                if user_agent.search(request_user_agent):
                    ignore = True
                    break

            # If there's already a key in the session for a valid user, then
            # we don't need to do anything. If the user isn't valid, then
            # get_user will return an anonymous user
            if get_user(request).is_anonymous() and not ignore:
                # If not, then we have to create a user, and log them in.
                from lazysignup.models import LazyUser
                user, username = LazyUser.objects.create_lazy_user()
                request.user = None
                user = authenticate(username=username)
                assert user, ("Lazy user creation and authentication "
                              "failed. Have you got "
                              "lazysignup.backends.LazySignupBackend in "
                              "AUTHENTICATION_BACKENDS?")
                # Set the user id in the session here to prevent the login
                # call cycling the session key.
                request.session[SESSION_KEY] = user.id
                login(request, user)
        return func(viewset, *args, **kwargs)

    return wraps(func)(wrapped)