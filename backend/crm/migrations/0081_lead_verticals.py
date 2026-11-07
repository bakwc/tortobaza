from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


SWEET_CLASSIFY = """You classify Telegram chat messages for a confectionery business Sweet Chill in Batumi.

Sweet Chill sells custom cakes, bento cakes, honey cakes (medovik), macarons, cupcakes, and related desserts.

The user message is the text of one Telegram message. Decide whether the author is a potential sales lead: they are looking to buy or order confectionery (asking where to order, price, recommendations, availability, delivery, or describing what they want to order).

Return is_lead false when the product is mentioned incidentally (general chat, jokes, news, someone else's business, unrelated context) and there is no sign the author wants to buy or order from a confectionery.

Return is_lead and explanation. explanation is one short sentence in Russian stating why this verdict was chosen."""

SWEET_GEO = """

The business only delivers in Batumi and Georgia. Return is_lead false when the author is clearly looking for a confectionery in another city or country, or mentions a metro station, a district, or a street that is not in Batumi. Batumi has no metro. If no location is mentioned, decide as usual.

The user message may start with "Post location: ..." and "Post topic: ...". A location or a topic that names another city or country means is_lead false. Batumi or Georgia means the geography fits. A topic may be unrelated to a place, for example "Cooking Threads"; ignore such a topic."""

SWEET_CONTEXT = """

The user message is a thread of posts. The target post is marked with [target]. The other posts are the conversation around it: the post it replies to and the replies under it.

Return is_lead false when the target post answers a question about another city or country, or about something unrelated to buying confectionery in Batumi. A reply that offers cakes only because someone asked what they could do for free, or that answers a request for another city, is not a lead."""

SWEET_PROFILE = """

The user message also contains the author's profile and their recent posts, under "=== Профиль пользователя ===" and "=== Последние сообщения пользователя ===".

Decide the author's city from the post location, the post topic, the thread, the profile, and the recent posts. Return is_lead true only when there is an explicit sign the author is in Batumi. Return is_lead false when another city is indicated, including other cities in Georgia, or when the city cannot be determined."""

BEAUTY_CLASSIFY = """You classify Telegram chat messages for beauty services in Batumi: makeup, hairstyles, and hair coloring.

The user message is the text of one Telegram message. Decide whether the author is a potential sales lead: they are looking to book or order makeup, a hairstyle, or hair coloring (asking where to book, price, recommendations, availability, a master, or describing what they want).

Return is_lead false when the service is mentioned incidentally (general chat, jokes, news, someone else's business, unrelated context) and there is no sign the author wants to book or order.

Return is_lead and explanation. explanation is one short sentence in Russian stating why this verdict was chosen."""

BEAUTY_GEO = """

The business only works in Batumi and Georgia. Return is_lead false when the author is clearly looking for makeup, a hairstyle, or hair coloring in another city or country, or mentions a metro station, a district, or a street that is not in Batumi. Batumi has no metro. If no location is mentioned, decide as usual.

The user message may start with "Post location: ..." and "Post topic: ...". A location or a topic that names another city or country means is_lead false. Batumi or Georgia means the geography fits. A topic may be unrelated to a place, for example "Cooking Threads"; ignore such a topic."""

BEAUTY_CONTEXT = """

The user message is a thread of posts. The target post is marked with [target]. The other posts are the conversation around it: the post it replies to and the replies under it.

Return is_lead false when the target post answers a question about another city or country, or about something unrelated to booking makeup, a hairstyle, or hair coloring in Batumi. A reply that offers these services only because someone asked what they could do for free, or that answers a request for another city, is not a lead."""

BEAUTY_PROFILE = """

The user message also contains the author's profile and their recent posts, under "=== Профиль пользователя ===" and "=== Последние сообщения пользователя ===".

Decide the author's city from the post location, the post topic, the thread, the profile, and the recent posts. Return is_lead true only when there is an explicit sign the author is in Batumi. Return is_lead false when another city is indicated, including other cities in Georgia, or when the city cannot be determined."""


def seed_verticals(apps, schema_editor):
    LeadVertical = apps.get_model("crm", "LeadVertical")
    SocialKeyword = apps.get_model("crm", "SocialKeyword")
    SocialMessage = apps.get_model("crm", "SocialMessage")
    SocialLead = apps.get_model("crm", "SocialLead")
    SocialSearchQuery = apps.get_model("crm", "SocialSearchQuery")
    sweet = LeadVertical.objects.create(
        slug="sweet_chill",
        name="Sweet Chill",
        enabled=True,
        telegram_chat_id=settings.TELEGRAM_LEADS_CHAT_ID,
        prompt_classify=SWEET_CLASSIFY,
        prompt_geo=SWEET_GEO,
        prompt_context=SWEET_CONTEXT,
        prompt_profile=SWEET_PROFILE,
    )
    LeadVertical.objects.create(
        slug="beauty",
        name="Макияж и причёски",
        enabled=True,
        telegram_chat_id="",
        prompt_classify=BEAUTY_CLASSIFY,
        prompt_geo=BEAUTY_GEO,
        prompt_context=BEAUTY_CONTEXT,
        prompt_profile=BEAUTY_PROFILE,
    )
    SocialKeyword.objects.update(vertical=sweet)
    for message in SocialMessage.objects.all().iterator():
        history = message.processing_history
        lead_history = [event for event in history if event.get("kind") != "context"]
        message_history = [event for event in history if event.get("kind") == "context"]
        SocialLead.objects.create(
            message=message,
            vertical=sweet,
            keyword_match=message.keyword_match,
            potential_lead=message.potential_lead,
            lead=message.lead,
            lead_notified=message.lead_notified,
            processing_history=lead_history,
        )
        if message_history != history:
            message.processing_history = message_history
            message.save(update_fields=["processing_history"])
    SocialSearchQuery.objects.create(
        query="батуми торт",
        kind="heavy",
        recent=False,
        post_limit=50,
        enabled=True,
        position=0,
    )
    SocialSearchQuery.objects.create(
        query="бенто батуми",
        kind="heavy",
        recent=False,
        post_limit=50,
        enabled=True,
        position=1,
    )
    SocialSearchQuery.objects.create(
        query="батуми",
        kind="light",
        recent=True,
        post_limit=38,
        enabled=True,
        position=2,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0080_socialmessage_processing_history"),
    ]

    operations = [
        migrations.CreateModel(
            name="LeadVertical",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=64, unique=True, verbose_name="Slug")),
                ("name", models.CharField(max_length=255, verbose_name="Name")),
                ("enabled", models.BooleanField(default=True, verbose_name="Enabled")),
                ("telegram_chat_id", models.CharField(blank=True, default="", max_length=64, verbose_name="Telegram chat id")),
                ("prompt_classify", models.TextField(verbose_name="Classify prompt")),
                ("prompt_geo", models.TextField(verbose_name="Geo prompt")),
                ("prompt_context", models.TextField(verbose_name="Context prompt")),
                ("prompt_profile", models.TextField(verbose_name="Profile prompt")),
            ],
            options={
                "verbose_name": "Lead vertical",
                "verbose_name_plural": "Lead verticals",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="SocialSearchQuery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("query", models.CharField(max_length=255, verbose_name="Query")),
                ("kind", models.CharField(max_length=16, verbose_name="Kind")),
                ("recent", models.BooleanField(default=False, verbose_name="Recent")),
                ("post_limit", models.PositiveIntegerField(verbose_name="Post limit")),
                ("enabled", models.BooleanField(default=True, verbose_name="Enabled")),
                ("position", models.PositiveIntegerField(default=0, verbose_name="Position")),
            ],
            options={
                "verbose_name": "Social search query",
                "verbose_name_plural": "Social search queries",
                "ordering": ["position", "id"],
            },
        ),
        migrations.AddField(
            model_name="socialkeyword",
            name="vertical",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="keywords",
                to="crm.leadvertical",
                verbose_name="Vertical",
            ),
        ),
        migrations.CreateModel(
            name="SocialLead",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("keyword_match", models.BooleanField(default=False, verbose_name="Keyword match")),
                ("potential_lead", models.BooleanField(blank=True, null=True, verbose_name="Potential lead")),
                ("lead", models.BooleanField(blank=True, null=True, verbose_name="Lead")),
                ("lead_notified", models.BooleanField(default=False, verbose_name="Lead notified")),
                ("processing_history", models.JSONField(default=list, verbose_name="Processing history")),
                (
                    "message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="leads",
                        to="crm.socialmessage",
                        verbose_name="Message",
                    ),
                ),
                (
                    "vertical",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="social_leads",
                        to="crm.leadvertical",
                        verbose_name="Vertical",
                    ),
                ),
            ],
            options={
                "verbose_name": "Social lead",
                "verbose_name_plural": "Social leads",
                "ordering": ["id"],
            },
        ),
        migrations.AddConstraint(
            model_name="sociallead",
            constraint=models.UniqueConstraint(fields=("message", "vertical"), name="uniq_sociallead_message_vertical"),
        ),
        migrations.RunPython(seed_verticals, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="socialkeyword",
            name="vertical",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="keywords",
                to="crm.leadvertical",
                verbose_name="Vertical",
            ),
        ),
        migrations.AlterField(
            model_name="socialkeyword",
            name="word",
            field=models.CharField(max_length=255, verbose_name="Word"),
        ),
        migrations.AddConstraint(
            model_name="socialkeyword",
            constraint=models.UniqueConstraint(fields=("vertical", "word"), name="uniq_socialkeyword_vertical_word"),
        ),
        migrations.RemoveField(model_name="socialmessage", name="keyword_match"),
        migrations.RemoveField(model_name="socialmessage", name="potential_lead"),
        migrations.RemoveField(model_name="socialmessage", name="lead"),
        migrations.RemoveField(model_name="socialmessage", name="lead_notified"),
    ]
