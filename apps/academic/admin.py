from django.contrib import admin
from django.utils.html import format_html
from .models import Subject, Topic, Question

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fields = ('text', 'cognitive_level', 'difficulty', 'correct_option', 'rasch_difficulty')
    show_change_link = True

class TopicInline(admin.TabularInline):
    model = Topic
    extra = 1
    fields = ('order', 'title')
    show_change_link = True

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'topics_count', 'total_questions_count', 'created_at')
    search_fields = ('name', 'code')
    inlines = [TopicInline]

    def topics_count(self, obj):
        count = obj.topics.count()
        return format_html('<span style="font-weight: bold; color: #4338ca;">{} ta mavzu</span>', count)
    topics_count.short_description = "Mavzular soni"

    def total_questions_count(self, obj):
        count = Question.objects.filter(topic__subject=obj).count()
        return format_html('<span style="font-weight: bold; color: #059669;">{} ta savol</span>', count)
    total_questions_count.short_description = "Jami savollar"

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('order', 'title', 'subject', 'questions_count', 'cognitive_breakdown')
    list_display_links = ('title',)
    list_filter = ('subject',)
    search_fields = ('title', 'description')
    list_editable = ('order',)
    ordering = ('subject', 'order')
    inlines = [QuestionInline]

    def questions_count(self, obj):
        count = obj.questions.count()
        return format_html('<b>{}</b> ta', count)
    questions_count.short_description = "Savollar"

    def cognitive_breakdown(self, obj):
        k = obj.questions.filter(cognitive_level='KNOWLEDGE').count()
        a = obj.questions.filter(cognitive_level='APPLICATION').count()
        r = obj.questions.filter(cognitive_level='REASONING').count()
        return format_html(
            '<span style="background:#dbeafe; color:#1e40af; padding:2px 6px; border-radius:4px; font-size:11px; margin-right:4px;">🔵 Bilish: {}</span>'
            '<span style="background:#d1fae5; color:#065f46; padding:2px 6px; border-radius:4px; font-size:11px; margin-right:4px;">🟢 Qo\'llash: {}</span>'
            '<span style="background:#f3e8ff; color:#6b21a8; padding:2px 6px; border-radius:4px; font-size:11px;">🟣 Mulohaza: {}</span>',
            k, a, r
        )
    cognitive_breakdown.short_description = "Kognitiv taqsimot"

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'topic', 'short_text', 'cognitive_level', 
        'difficulty', 'correct_option', 'rasch_difficulty', 'weight_display'
    )
    list_display_links = ('id', 'short_text')
    list_filter = ('cognitive_level', 'difficulty', 'topic__subject', 'topic')
    search_fields = ('text', 'option_a', 'option_b', 'option_c', 'option_d', 'explanation')
    list_editable = ('cognitive_level', 'difficulty', 'correct_option')
    list_per_page = 25
    actions = ['make_knowledge', 'make_application', 'make_reasoning', 'make_easy', 'make_medium', 'make_hard']

    def short_text(self, obj):
        return obj.text[:65] + ("..." if len(obj.text) > 65 else "")
    short_text.short_description = "Savol matni"

    def cognitive_level_badge(self, obj):
        if obj.cognitive_level == 'KNOWLEDGE':
            return format_html('<span style="background:#dbeafe; color:#1e40af; font-weight:bold; padding:3px 8px; border-radius:12px; font-size:11px;">🔵 Bilish</span>')
        elif obj.cognitive_level == 'APPLICATION':
            return format_html('<span style="background:#d1fae5; color:#065f46; font-weight:bold; padding:3px 8px; border-radius:12px; font-size:11px;">🟢 Qo\'llash</span>')
        else:
            return format_html('<span style="background:#f3e8ff; color:#6b21a8; font-weight:bold; padding:3px 8px; border-radius:12px; font-size:11px;">🟣 Mulohaza</span>')
    cognitive_level_badge.short_description = "Kognitiv Modul"

    def difficulty_badge(self, obj):
        if obj.difficulty == 'EASY':
            return format_html('<span style="background:#f1f5f9; color:#334155; padding:2px 6px; border-radius:4px; font-size:11px;">Oson</span>')
        elif obj.difficulty == 'MEDIUM':
            return format_html('<span style="background:#fef3c7; color:#92400e; padding:2px 6px; border-radius:4px; font-size:11px;">O\'rta</span>')
        else:
            return format_html('<span style="background:#ffe4e6; color:#9f1239; padding:2px 6px; border-radius:4px; font-size:11px;">Qiyin</span>')
    difficulty_badge.short_description = "Qiyinchilik"

    def weight_display(self, obj):
        return format_html('<span style="font-family:monospace; font-weight:bold; color:#4338ca;">{}</span>', obj.weight)
    weight_display.short_description = "Rasch vazni"

    # Admin Actions
    @admin.action(description="Tanlanganlarni 'Bilish' moduliga o'tkazish")
    def make_knowledge(self, request, queryset):
        updated = queryset.update(cognitive_level='KNOWLEDGE')
        self.message_user(request, f"{updated} ta savol 'Bilish' moduliga o'tkazildi.")

    @admin.action(description="Tanlanganlarni 'Qo'llash' moduliga o'tkazish")
    def make_application(self, request, queryset):
        updated = queryset.update(cognitive_level='APPLICATION')
        self.message_user(request, f"{updated} ta savol 'Qo'llash' moduliga o'tkazildi.")

    @admin.action(description="Tanlanganlarni 'Mulohaza yuritish' moduliga o'tkazish")
    def make_reasoning(self, request, queryset):
        updated = queryset.update(cognitive_level='REASONING')
        self.message_user(request, f"{updated} ta savol 'Mulohaza yuritish' moduliga o'tkazildi.")

    @admin.action(description="Tanlanganlarni 'Oson' qilib belgilash")
    def make_easy(self, request, queryset):
        queryset.update(difficulty='EASY', rasch_difficulty=-1.0)

    @admin.action(description="Tanlanganlarni 'O'rta' qilib belgilash")
    def make_medium(self, request, queryset):
        queryset.update(difficulty='MEDIUM', rasch_difficulty=0.1)

    @admin.action(description="Tanlanganlarni 'Qiyin' qilib belgilash")
    def make_hard(self, request, queryset):
        queryset.update(difficulty='HARD', rasch_difficulty=1.4)
