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

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


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
    message = "Your account is not fully verified. Please verify your email and phone number to access this feature."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.email_verified and request.user.phone_verified


class IsChamaAdmin(permissions.BasePermission):
    message = "Only chama officials (chairperson, treasurer, or secretary) can perform this action."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return any([
            request.user.has_role(Role.CHAMA_TREASURER),
            request.user.has_role(Role.CHAMA_CHAIRPERSON),
            request.user.has_role(Role.CHAMA_SECRETARY),
        ])


class IsInvestorOrInstitutional(permissions.BasePermission):
    message = "Only verified investors or institutional buyers can access this feature."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return any([
            request.user.has_role(Role.INVESTOR),
            request.user.has_role(Role.INSTITUTIONAL_BUYER),
        ])


class IsPlatformStaff(permissions.BasePermission):
    message = "Only platform administrators or support agents can access this feature."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return any([
            request.user.has_role(Role.PLATFORM_ADMIN),
            request.user.has_role(Role.SUPPORT_AGENT),
            request.user.is_staff,
        ])