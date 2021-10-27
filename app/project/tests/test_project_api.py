from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Project, Application, Software, Tag

from project.serializers import ProjectSerializer, ProjectDetailSerializer


PROJECTS_URL = reverse('project:project-list')


def detail_url(project_id):
    """Return project detail URL"""
    return reverse('project:project-detail', args=[project_id])


def sample_tag(name='High School'):
    """Create and return a sample tag"""
    return Tag.objects.create(name=name)


def sample_software(**params):
    """Create and return a sample software"""
    defaults = {
        'name': 'Adinkra',
        'default_file': 'Cool spiral',
        'application': 1,
    }

    defaults.update(params)
    return Software.objects.create(**defaults)


def sample_project(user, **params):
    """Create and return a sample project"""

    defaults = {
        'title': 'Cool Project',
        'application': 1,
        'data': 'Sample data',
        'thumbnail': 'Sample thumbnail',
    }
    defaults.update(params)

    return Project.objects.create(owner=user, **defaults)


def sample_application(**params):
    """Create and return a sample application"""

    defaults = {
        'name': "Test",
        'link': 'Link',
        'description': 'Text'
    }
    defaults.update(params)
    return Application.objects.create(**defaults)


class PublicProjectApiTests(TestCase):
    """Test unauthenticated project api access"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required"""
        res = self.client.get(PROJECTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateProjectApiTests(TestCase):
    """Test authenticated project api access"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'test',
            'test@csdt.org',
            'testpass'
        )
        self.client.force_authenticate(self.user)

        self.application = sample_application()

    def test_retrieve_projects(self):
        """Test retrieving a list of projects"""
        sample_project(user=self.user, application=self.application)
        sample_project(user=self.user, application=self.application)

        res = self.client.get(PROJECTS_URL)

        projects = Project.objects.all().order_by('-id')
        serializer = ProjectSerializer(projects, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_projects_limited_to_user(self):
        user2 = get_user_model().objects.create_user(
            'other',
            'other@csdt.org',
            'otherpass'
        )
        sample_project(user=user2, application=self.application)
        sample_project(user=self.user, application=self.application)

        res = self.client.get(PROJECTS_URL)

        project = Project.objects.filter(owner=self.user)
        serializer = ProjectSerializer(project, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data, serializer.data)

    def test_view_project_detail(self):
        """Test viewing project detail"""
        project = sample_project(user=self.user, application=self.application)
        project.tags.add(sample_tag())

        url = detail_url(project.id)
        res = self.client.get(url)

        serializer = ProjectDetailSerializer(project)
        self.assertEqual(res.data, serializer.data)

    def test_create_basic_project(self):
        """Test creating basic project"""
        payload = {
            'title': 'Adinkra Spirals',
            'application': self.application.pk,
            'data': 'Sample data',
            'thumbnail': 'Sample thumbnail',
        }

        res = self.client.post(PROJECTS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        project = Project.objects.get(id=res.data['id'])
        for key in payload.keys():
            if key == 'application':
                self.assertEqual(payload['application'],
                                 getattr(project, 'application').pk)
            else:
                self.assertEqual(payload[key], getattr(project, key))

    def test_create_project_with_tags(self):
        """Test creating project with tags"""
        tag1 = sample_tag(name="Cornrow Curves")
        tag2 = sample_tag(name="High School")
        payload = {
            'title': 'Variable Curves',
            'application': self.application.pk,
            'data': 'Another sample data',
            'thumbnail': 'Another sample thumbnail',
            'tags': [tag1.id, tag2.id]
        }

        res = self.client.post(PROJECTS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        project = Project.objects.get(id=res.data['id'])
        tags = project.tags.all()
        self.assertEqual(tags.count(), 2)
        self.assertIn(tag1, tags)
        self.assertIn(tag2, tags)
