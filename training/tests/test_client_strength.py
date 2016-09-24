from django.test import Client, TestCase
from django.contrib.auth.models import User

from training import models, units


class ClienStrengthTestCase(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='grzegorz', email='', password='z')
        self.client = Client()

    def _expect_workout_page(self, workout_id, status_code=200):
        response = self.client.get('/workout/{}'.format(workout_id), follow=True)
        self.assertEqual(status_code, response.status_code)

    def test_create_workout(self):
        response = self.client.post('/login/', {'username': 'grzegorz', 'password': 'z'})
        self.assertEqual(302, response.status_code)
        self.assertEqual('/dashboard', response['Location'])

        response = self.client.get('/start_workout', follow=True)
        self.assertEqual(200, response.status_code)
        self.assertIsNotNone(response.context['workout'])

        workout_id = response.context['workout'].id

        self._expect_workout_page(workout_id)

        response = self.client.post('/add_excercise/{}/'.format(workout_id), {'name': 'push-up'}, follow=True)
        self.assertEqual(200, response.status_code)

        response = self.client.post('/finish_workout/{}'.format(workout_id), follow=True)
        self.assertEqual(200, response.status_code)

        response = self.client.post('/dashboard', follow=True)
        self.assertEqual(200, response.status_code)
        statistics = response.context['statistics']

        workout = statistics.previous_workouts()[0]
        self.assertIsNotNone(workout.started)
        self.assertIsNotNone(workout.finished)

        self.assertEqual(1, workout.excercise_set.count())

        self.assertEqual(units.Volume(reps=0), workout.volume())

        response = self.client.post('/delete_workout/{}/'.format(workout_id), follow=True)
        self.assertEqual(200, response.status_code)

        self._expect_workout_page(workout_id, status_code=404)