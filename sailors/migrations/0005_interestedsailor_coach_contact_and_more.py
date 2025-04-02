# Generated by Django 5.1.7 on 2025-03-31 23:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sailors', '0004_interestedsailor_last_heard_from_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='interestedsailor',
            name='coach_contact',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='interestedsailor',
            name='coach_name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='interestedsailor',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.AddField(
            model_name='interestedsailor',
            name='gpa',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='interestedsailor',
            name='hometown',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='interestedsailor',
            name='major',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='interestedsailor',
            name='phone',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='interestedsailor',
            name='position',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='interestedsailor',
            name='references',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='interestedsailor',
            name='size',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
