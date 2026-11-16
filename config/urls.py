from django.contrib import admin
from django.urls import path
from apps.analytics import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/students/add/', views.add_student_view, name='add_student'),
    path('teacher/grade/add/', views.add_formative_grade, name='add_formative_grade'),
    path('teacher/questions/upload/', views.upload_questions_view, name='upload_questions'),
    path('student/', views.student_portal, name='student_portal'),
    path('student/<int:student_id>/', views.student_portal, name='student_portal_id'),
    path('quiz/<int:topic_id>/', views.take_formative_quiz, name='take_formative_quiz'),
    path('quiz/<int:topic_id>/<int:student_id>/', views.take_formative_quiz, name='take_formative_quiz_student'),
    path('exam/start/', views.start_adaptive_exam, name='start_adaptive_exam'),
    path('exam/start/<int:student_id>/', views.start_adaptive_exam, name='start_adaptive_exam_student'),
    path('exam/<int:exam_id>/', views.take_adaptive_exam, name='take_adaptive_exam'),
    path('exam/<int:exam_id>/result/', views.exam_result, name='exam_result'),
]
