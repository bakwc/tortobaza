from django.conf import settings
from django.db import models
from django.db.models import Case, IntegerField, When
from django.utils.translation import gettext_lazy as _


class WishlistItem(models.Model):
    title = models.CharField(max_length=200, verbose_name=_("Title"))
    purpose = models.TextField(blank=True, default="", verbose_name=_("Purpose"))
    priority = models.PositiveIntegerField(verbose_name=_("Priority"))
    cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Cost"),
    )

    class Meta:
        ordering = ["priority", "id"]
        verbose_name = _("Wishlist item")
        verbose_name_plural = _("Wishlist items")

    def __str__(self) -> str:
        return self.title


class IdeaQuerySet(models.QuerySet):
    def ordered(self):
        rank = Case(
            When(status=Idea.STATUS_DOING, then=0),
            When(status=Idea.STATUS_PLANNED, then=1),
            When(status=Idea.STATUS_UNKNOWN, then=2),
            When(status=Idea.STATUS_REJECTED, then=3),
            When(status=Idea.STATUS_SUCCEEDED, then=4),
            When(status=Idea.STATUS_FAILED, then=5),
            output_field=IntegerField(),
        )
        return self.annotate(status_rank=rank).order_by("status_rank", "priority", "id")


class Idea(models.Model):
    STATUS_DOING = "doing"
    STATUS_PLANNED = "planned"
    STATUS_UNKNOWN = "unknown"
    STATUS_REJECTED = "rejected"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_DOING, _("Doing now")),
        (STATUS_PLANNED, _("Will do")),
        (STATUS_UNKNOWN, _("Unknown")),
        (STATUS_REJECTED, _("Will not do")),
        (STATUS_SUCCEEDED, _("Checked, took off")),
        (STATUS_FAILED, _("Checked, did not take off")),
    ]

    priority = models.PositiveIntegerField(verbose_name=_("Priority"))
    problem = models.TextField(blank=True, default="", verbose_name=_("Problem"))
    description = models.TextField(verbose_name=_("Description"))
    cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Cost"),
    )
    duration = models.DurationField(null=True, blank=True, verbose_name=_("Duration"))
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_UNKNOWN,
        verbose_name=_("Status"),
    )

    objects = IdeaQuerySet.as_manager()

    class Meta:
        verbose_name = _("Idea")
        verbose_name_plural = _("Ideas")

    def __str__(self) -> str:
        return self.description


class Task(models.Model):
    STATUS_TODO = "todo"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_DONE = "done"
    STATUS_CHOICES = [
        (STATUS_TODO, _("To do")),
        (STATUS_IN_PROGRESS, _("In progress")),
        (STATUS_DONE, _("Done")),
    ]

    title = models.CharField(max_length=200, verbose_name=_("Title"))
    description = models.TextField(blank=True, default="", verbose_name=_("Description"))
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_TODO,
        verbose_name=_("Status"),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="authored_tasks",
        on_delete=models.PROTECT,
        verbose_name=_("Author"),
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="assigned_tasks",
        on_delete=models.PROTECT,
        verbose_name=_("Assignee"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Completed at"))

    class Meta:
        ordering = ["id"]
        verbose_name = _("Task")
        verbose_name_plural = _("Tasks")

    def __str__(self) -> str:
        return self.title
