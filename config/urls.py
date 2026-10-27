from django.contrib import admin
from django.urls import include, path
from practice.admin_views import submissions, email_settings, restore_content, preview, bulk_questions
admin.site.site_header = 'RE Revi · Administration'
admin.site.site_title = 'RE Revi administration'
admin.site.index_title = 'Manage RE Revi'
urlpatterns = [path('admin/questions/bulk-edit/',admin.site.admin_view(bulk_questions),name='admin_bulk_questions'),path('admin/notifications/settings/',admin.site.admin_view(email_settings),name='admin_email_settings'),path('admin/content/restore/<int:revision_id>/',admin.site.admin_view(restore_content),name='admin_restore_content'),path('admin/preview/<str:kind>/<str:object_id>/',admin.site.admin_view(preview),name='admin_preview'),path('admin/submissions/', admin.site.admin_view(submissions), name='admin_submissions'), path('admin/', admin.site.urls), path('', include('practice.urls'))]
