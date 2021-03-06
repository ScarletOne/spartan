import os
import datetime
import pytz

from django.test import Client, TestCase
from django.contrib.auth.models import User

from training import models, units


GPX_DIR = os.path.dirname(os.path.abspath(__file__))


class ClienStrengthTestCase(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='grzegorz', email='', password='z')
        self.client = Client()

    def _get(self, uri, status_code=200):
        response = self.client.get(uri, follow=True)
        self.assertEqual(status_code, response.status_code)
        return response

    def _post(self, uri, data={}, status_code=200):
        response = self.client.post(uri, data, follow=True)
        self.assertEqual(status_code, response.status_code)
        return response

    def _expect_workout_page(self, workout_id, status_code=200):
        return self._get('/workout/{}'.format(workout_id), status_code=status_code)

    def _expect_to_be_logged_in(self):
        self._post('/login/', {'username': 'grzegorz', 'password': 'z'})

    def _expect_workout_to_be_created(self):
        workout = self._get('/start_workout').context['workout']
        self._expect_workout_page(workout.id)

    def _get_statistics_from_dashboard(self):
        return self._get('/dashboard').context['statistics']

    def test_create_workout_and_delete_it(self):
        self._expect_to_be_logged_in()
        self._expect_workout_to_be_created()

        statistics = self._get_statistics_from_dashboard()
        workout = statistics.previous_workouts()[0]

        self._post('/delete_workout/{}/'.format(workout.id))

        self._expect_workout_page(workout.id, status_code=404)

    def test_add_some_excercises_and_reps(self):
        self._expect_to_be_logged_in()
        self._expect_workout_to_be_created()

        statistics = self._get_statistics_from_dashboard()
        workout = statistics.previous_workouts()[0]

        self.assertIsNone(workout.started)
        self.assertIsNone(workout.finished)

        self._post('/add_excercise/{}/'.format(workout.id), {'name': 'push-up'})

        statistics = self._get_statistics_from_dashboard()
        workout = statistics.previous_workouts()[0]

        self.assertIsNotNone(workout.started)
        self.assertIsNone(workout.finished)

        excercise = workout.excercise_set.latest('pk')

        self._post('/add_reps/{}/'.format(excercise.id), {'reps': '10'})
        self._post('/add_excercise/{}/'.format(workout.id), {'name': 'pull-up'})

        excercise = workout.excercise_set.latest('pk')

        self._post('/add_reps/{}/'.format(excercise.id), {'reps': '5'})
        self._post('/add_reps/{}/'.format(excercise.id), {'reps': '5'})

        self.assertEqual(units.Volume(reps=20), workout.volume())
        self.assertEqual(20, statistics.total_reps())

        self._post('/finish_workout/{}'.format(workout.id))

        statistics = self._get_statistics_from_dashboard()
        workout = statistics.previous_workouts()[0]

        self.assertIsNotNone(workout.started)
        self.assertIsNotNone(workout.finished)

    def test_gpx_import(self):
        self._expect_to_be_logged_in()

        gpx_file = os.path.join(GPX_DIR, "3p_simplest.gpx")

        with open(gpx_file, 'r') as f:
            self._post('/upload_gpx/', {'gpxfile': f})

        statistics = self._get_statistics_from_dashboard()
        self.assertTrue(statistics.previous_workouts().count() > 0)
        workout = statistics.previous_workouts()[0]

        self.assertTrue(workout.is_gpx());
        self.assertEqual(datetime.datetime(2016, 7, 30, 6, 22, 5, tzinfo=pytz.utc), workout.started)
        self.assertEqual(datetime.datetime(2016, 7, 30, 6, 22, 7, tzinfo=pytz.utc), workout.finished)

        gpx_workout = workout.gpx_set.get()
        self.assertEqual("running", gpx_workout.activity_type.lower())
        self.assertEqual(4, gpx_workout.length_2d)

        self.assertEqual('4m', statistics.total_km())

        gpx_file = os.path.join(GPX_DIR, "3p_simplest_2.gpx")

        with open(gpx_file, 'r') as f:
            self._post('/upload_gpx/', {'gpxfile': f})

        self.assertEqual('8m', statistics.total_km())

        gpx_file = os.path.join(GPX_DIR, "3p_cycling.gpx")

        with open(gpx_file, 'r') as f:
            self._post('/upload_gpx/', {'gpxfile': f})

        self.assertEqual('12m', statistics.total_km())
