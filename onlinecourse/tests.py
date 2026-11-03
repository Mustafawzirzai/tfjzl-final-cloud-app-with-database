from django.contrib.auth.models import User
from django.test import TestCase

from .models import Choice, Course, Enrollment, Question, Submission


class ExamFlowTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='learner', password='pass12345')
		self.other_user = User.objects.create_user(username='other', password='pass12345')
		self.course = Course.objects.create(name='Django Basics', description='Learn Django')
		self.enrollment = Enrollment.objects.create(user=self.user, course=self.course)
		self.question = Question.objects.create(
			course=self.course,
			question_text='Which framework is this course about?',
		)
		self.correct_choice = Choice.objects.create(
			question=self.question,
			choice_text='Django',
			is_correct=True,
		)
		self.incorrect_choice = Choice.objects.create(
			question=self.question,
			choice_text='Flask',
			is_correct=False,
		)

	def test_root_url_displays_course_list(self):
		response = self.client.get('/')

		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, 'onlinecourse/course_list_bootstrap.html')

	def test_submit_creates_submission_and_displays_grade(self):
		self.client.force_login(self.user)

		response = self.client.post(
			f'/onlinecourse/{self.course.id}/submit/',
			{f'choice_{self.question.id}': self.correct_choice.id},
		)

		submission = Submission.objects.get(enrollment=self.enrollment)
		self.assertRedirects(
			response,
			f'/onlinecourse/{self.course.id}/submission/{submission.id}/',
		)
		result = self.client.get(response.url)
		self.assertEqual(result.status_code, 200)
		self.assertEqual(result.context['grade'], 100)
		self.assertContains(result, 'Passed with a score of 100%')

	def test_submit_ignores_choices_from_another_course(self):
		self.client.force_login(self.user)
		other_course = Course.objects.create(name='Other Course', description='Another course')
		other_question = Question.objects.create(course=other_course, question_text='Other question')
		other_choice = Choice.objects.create(question=other_question, choice_text='Other answer', is_correct=True)

		self.client.post(
			f'/onlinecourse/{self.course.id}/submit/',
			{f'choice_{self.question.id}': other_choice.id},
		)

		submission = Submission.objects.get(enrollment=self.enrollment)
		self.assertFalse(submission.choices.exists())

	def test_submission_result_is_private_to_enrolled_user(self):
		submission = Submission.objects.create(enrollment=self.enrollment)
		submission.choices.add(self.incorrect_choice)
		self.client.force_login(self.other_user)

		response = self.client.get(
			f'/onlinecourse/{self.course.id}/submission/{submission.id}/'
		)

		self.assertEqual(response.status_code, 404)
