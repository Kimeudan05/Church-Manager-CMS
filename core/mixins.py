from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect

class GroupLeaderRequiredMixin(AccessMixin):
    """Verify that the current user is a group leader"""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return  self.handle_no_permission()
        if not hasattr(request.user, 'church_role'):
            return self.handle_no_permission()
        if request.user.church_role.role_type !='group_leader':
            return self.handle_no_permission()
        return  super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(AccessMixin):
    """Verify that the current user is a admin user"""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not hasattr(request.user,'church_role'):
            return self.handle_no_permission()
        if request.user.church_role.role_type not in ['super_admin','church_admin']:
            return self.handle_no_permission()
        return  super().dispatch(request, *args, **kwargs)