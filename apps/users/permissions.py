from rest_framework import permissions
from apps.users.models import Role


class HasRolePermission(permissions.BasePermission):

    def __init__(self, required_role):
        self.required_role = required_role

    def __call__(self):
        return self

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.has_role(self.required_role)


class HasAnyRolePermission(permissions.BasePermission):

    def __init__(self, *required_roles):
        self.required_roles = required_roles

    def __call__(self):
        return self

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return any(request.user.has_role(role) for role in self.required_roles)


class IsVerifiedUser(permissions.BasePermission):

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.email_verified and request.user.phone_verified


class IsChamaAdmin(permissions.BasePermission):

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return any([
            request.user.has_role(Role.CHAMA_TREASURER),
            request.user.has_role(Role.CHAMA_CHAIRPERSON),
            request.user.has_role(Role.CHAMA_SECRETARY),
        ])


class IsInvestorOrInstitutional(permissions.BasePermission):

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return any([
            request.user.has_role(Role.INVESTOR),
            request.user.has_role(Role.INSTITUTIONAL_BUYER),
        ])


class IsPlatformStaff(permissions.BasePermission):

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return any([
            request.user.has_role(Role.PLATFORM_ADMIN),
            request.user.has_role(Role.SUPPORT_AGENT),
            request.user.is_staff,
        ])