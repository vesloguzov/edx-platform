'''
django admin pages for courseware model
'''
from django import forms
from config_models.admin import ConfigurationModelAdmin

from student.models import UserProfile, UserTestGroup, CourseEnrollmentAllowed, DashboardConfiguration
from student.models import CourseEnrollment, Registration, PendingNameChange, CourseAccessRole
from ratelimitbackend import admin
from student.roles import REGISTERED_ACCESS_ROLES


class CourseAccessRoleForm(forms.ModelForm):
    """Form for adding new Course Access Roles view the Django Admin Panel."""
    class Meta:
        model = CourseAccessRole

    COURSE_ACCESS_ROLES = [(role_name, role_name) for role_name in REGISTERED_ACCESS_ROLES.keys()]
    role = forms.ChoiceField(choices=COURSE_ACCESS_ROLES)


class CourseAccessRoleAdmin(admin.ModelAdmin):
    """Admin panel for the Course Access Role. """
    form = CourseAccessRoleForm
    raw_id_fields = ("user",)
    list_display = (
        'id', 'user', 'org', 'course_id', 'role'
    )


class CourseEnrollmentAdmin(admin.ModelAdmin):
    """
    Admin panel for CourseEnrollment with quick search by username or email
    """
    list_select_related = True
    list_display = (
        'username',
        'email',
        'course_id',
        'mode',
        'is_active',
    )
    list_filter = (
        'is_active',
    )
    search_fields = (
        'user__username',
        'user__email',
    )

    def username(self, obj):
        return obj.user.username

    def email(self, obj):
        return obj.user.email


class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin panel for UserProfile with quick search by username, email or nickname
    """
    list_select_related = True
    list_display = (
        'username',
        'email',
        'nickname',
        'name',
        'birthdate',
        'city',
    )
    search_fields = (
        'user__username',
        'user__email',
        'nickname',
    )

    def username(self, obj):
        return obj.user.username

    def email(self, obj):
        return obj.user.email


admin.site.register(UserProfile, UserProfileAdmin)

admin.site.register(UserTestGroup)

admin.site.register(CourseEnrollment, CourseEnrollmentAdmin)

admin.site.register(CourseEnrollmentAllowed)

admin.site.register(Registration)

admin.site.register(PendingNameChange)

admin.site.register(CourseAccessRole, CourseAccessRoleAdmin)

admin.site.register(DashboardConfiguration, ConfigurationModelAdmin)
