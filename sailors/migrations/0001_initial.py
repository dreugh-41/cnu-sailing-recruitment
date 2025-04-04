# Generated by Django 5.1.7 on 2025-03-25 01:33

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='RegattaType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('weight', models.FloatField(default=1.0)),
            ],
        ),
        migrations.CreateModel(
            name='School',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Regatta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('url', models.URLField(unique=True)),
                ('date', models.DateField()),
                ('season', models.CharField(max_length=10)),
                ('is_jv', models.BooleanField(default=False)),
                ('regatta_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sailors.regattatype')),
            ],
        ),
        migrations.CreateModel(
            name='Sailor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('elo_rating', models.FloatField(default=1000)),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sailors.school')),
            ],
            options={
                'unique_together': {('name', 'school')},
            },
        ),
        migrations.CreateModel(
            name='Result',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('division', models.CharField(max_length=5)),
                ('position', models.CharField(max_length=50)),
                ('place', models.IntegerField()),
                ('regatta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sailors.regatta')),
                ('sailor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sailors.sailor')),
            ],
            options={
                'unique_together': {('sailor', 'regatta', 'division', 'position')},
            },
        ),
    ]
