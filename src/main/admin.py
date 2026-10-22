from django.contrib import admin

from main.models import Category, Entry, Goal


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'kind', 'owner', 'created_at')
    list_filter = ('kind',)
    search_fields = ('name', 'owner__username')


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ('description', 'kind', 'amount', 'occurred_on', 'owner', 'category')
    list_filter = ('kind', 'occurred_on')
    search_fields = ('description', 'owner__username', 'note')
    date_hierarchy = 'occurred_on'


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'current_amount', 'target_amount', 'target_date')
    search_fields = ('name', 'owner__username')
    list_filter = ('target_date',)
