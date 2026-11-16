from django.contrib import admin
from django.utils.html import format_html
from .models import FormativeGrade, StudentTopicMastery, QuizAttempt, SummativeExam, SummativeExamQuestion
from apps.analytics.services import update_student_topic_mastery

class SummativeExamQuestionInline(admin.TabularInline):
    model = SummativeExamQuestion
    extra = 0
    fields = ('question_text', 'cognitive_level_display', 'is_targeted_weak', 'student_answer', 'is_correct_badge', 'weight')
    readonly_fields = ('question_text', 'cognitive_level_display', 'is_correct_badge', 'weight')
    can_delete = False

    def question_text(self, obj):
        return obj.question.text[:60] + "..." if len(obj.question.text) > 60 else obj.question.text
    question_text.short_description = "Savol matni"

    def cognitive_level_display(self, obj):
        return obj.question.get_cognitive_level_display()
    cognitive_level_display.short_description = "Kognitiv Modul"

    def is_correct_badge(self, obj):
        if obj.is_correct:
            return format_html('<span style="color:#059669; font-weight:bold;">✔ To\'g\'ri</span>')
        return format_html('<span style="color:#dc2626; font-weight:bold;">✖ Noto\'g\'ri</span>')
    is_correct_badge.short_description = "Natija"

@admin.register(FormativeGrade)
class FormativeGradeAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'topic', 'grade_type_badge', 'score_badge', 'comment', 'date')
    list_filter = ('grade_type', 'date', 'topic__subject')
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'topic__title')
    list_per_page = 25
    actions = ['recalculate_mastery_for_selected']

    def grade_type_badge(self, obj):
        colors = {
            'ACTIVITY': '#0284c7',
            'HOMEWORK': '#7c3aed',
            'QUIZ': '#ea580c'
        }
        color = colors.get(obj.grade_type, '#475569')
        return format_html(
            '<span style="background:{}15; color:{}; border:1px solid {}40; padding:2px 8px; border-radius:10px; font-weight:600; font-size:11px;">{}</span>',
            color, color, color, obj.get_grade_type_display()
        )
    grade_type_badge.short_description = "Baho turi"

    def score_badge(self, obj):
        score_color = "#059669" if obj.score >= 70 else ("#d97706" if obj.score >= 60 else "#dc2626")
        return format_html(
            '<span style="font-weight:bold; color:{}; font-size:12px;">{}/{}</span>',
            score_color, obj.score, obj.max_score
        )
    score_badge.short_description = "Ball"

    @admin.action(description="Tanlangan baholar bo'yicha o'zlashtirishni qayta hisoblash")
    def recalculate_mastery_for_selected(self, request, queryset):
        count = 0
        for grade in queryset:
            update_student_topic_mastery(grade.student, grade.topic)
            count += 1
        self.message_user(request, f"{count} ta yozuv bo'yicha o'zlashtirish ko'rsatkichlari qayta hisoblandi.")

@admin.register(StudentTopicMastery)
class StudentTopicMasteryAdmin(admin.ModelAdmin):
    list_display = ('student', 'topic', 'mastery_bar', 'is_weak_badge', 'attempts_count', 'last_evaluated')
    list_filter = ('is_weak', 'topic__subject')
    search_fields = ('student__username', 'student__first_name', 'topic__title')
    list_per_page = 25

    def mastery_bar(self, obj):
        percent = obj.mastery_percentage
        color = "#059669" if percent >= 70 else ("#d97706" if percent >= 60 else "#dc2626")
        return format_html(
            '<div style="width:120px; background:#e2e8f0; border-radius:6px; overflow:hidden; display:inline-block; vertical-align:middle; margin-right:8px;">'
            '<div style="width:{}%; background:{}; height:10px;"></div></div>'
            '<span style="font-weight:bold; color:{}; font-size:11px;">{}%</span>',
            percent, color, color, percent
        )
    mastery_bar.short_description = "O'zlashtirish foizi"

    def is_weak_badge(self, obj):
        if obj.is_weak:
            return format_html('<span style="background:#ffe4e6; color:#9f1239; font-weight:bold; padding:2px 8px; border-radius:10px; font-size:11px;">🔴 Zaif nuqta</span>')
        return format_html('<span style="background:#d1fae5; color:#065f46; font-weight:bold; padding:2px 8px; border-radius:10px; font-size:11px;">🟢 O\'zlashtirilgan</span>')
    is_weak_badge.short_description = "Holat"

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'topic', 'score_display', 'correct_answers', 'total_questions', 'created_at')
    list_filter = ('topic__subject', 'created_at')
    search_fields = ('student__username', 'topic__title')

    def score_display(self, obj):
        color = "#059669" if obj.score >= 70 else "#dc2626"
        return format_html('<b style="color:{};">{}%</b>', color, obj.score)
    score_display.short_description = "Natija"

@admin.register(SummativeExam)
class SummativeExamAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'student', 'subject', 'exam_type', 'status_badge', 
        'cognitive_scores_display', 'actual_score', 'bonus_applied', 'final_score', 
        'dopusk_granted', 'created_at'
    )
    list_filter = ('status', 'exam_type', 'dopusk_granted', 'subject')
    search_fields = ('student__username', 'student__first_name', 'student__last_name')
    readonly_fields = ('predicted_score', 'actual_score', 'bonus_applied', 'final_score', 'knowledge_score', 'application_score', 'reasoning_score')
    inlines = [SummativeExamQuestionInline]
    list_per_page = 25

    def status_badge(self, obj):
        if obj.status == 'COMPLETED':
            return format_html('<span style="background:#d1fae5; color:#065f46; font-weight:bold; padding:2px 8px; border-radius:10px; font-size:11px;">Yakunlangan</span>')
        elif obj.status == 'IN_PROGRESS':
            return format_html('<span style="background:#fef3c7; color:#92400e; font-weight:bold; padding:2px 8px; border-radius:10px; font-size:11px;">Jarayonda</span>')
        return format_html('<span style="background:#f1f5f9; color:#475569; font-weight:bold; padding:2px 8px; border-radius:10px; font-size:11px;">Kutilmoqda</span>')
    status_badge.short_description = "Holati"

    def cognitive_scores_display(self, obj):
        if obj.status != 'COMPLETED':
            return "-"
        return format_html(
            '<span style="font-size:10px; font-weight:bold;">'
            '<span style="color:#1e40af;">🔵 B: {}%</span> | '
            '<span style="color:#065f46;">🟢 Q: {}%</span> | '
            '<span style="color:#6b21a8;">🟣 M: {}%</span>'
            '</span>',
            obj.knowledge_score, obj.application_score, obj.reasoning_score
        )
    cognitive_scores_display.short_description = "Modullar (B / Q / M)"

@admin.register(SummativeExamQuestion)
class SummativeExamQuestionAdmin(admin.ModelAdmin):
    list_display = ('exam', 'question_short', 'cognitive_level', 'is_targeted_weak', 'student_answer', 'is_correct_badge', 'weight')
    list_filter = ('is_correct', 'is_targeted_weak', 'question__cognitive_level')
    search_fields = ('exam__student__username', 'question__text')

    def question_short(self, obj):
        return obj.question.text[:50] + "..." if len(obj.question.text) > 50 else obj.question.text
    question_short.short_description = "Savol"

    def cognitive_level(self, obj):
        return obj.question.get_cognitive_level_display()
    cognitive_level.short_description = "Modul"

    def is_correct_badge(self, obj):
        if obj.is_correct:
            return format_html('<span style="color:#059669; font-weight:bold;">To\'g\'ri</span>')
        return format_html('<span style="color:#dc2626; font-weight:bold;">Noto\'g\'ri</span>')
    is_correct_badge.short_description = "Natija"
