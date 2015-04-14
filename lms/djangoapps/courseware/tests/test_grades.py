"""
Test grade calculation.
"""
from django.http import Http404
from django.test.utils import override_settings
from django.test.client import RequestFactory
from django.core.exceptions import SuspiciousOperation
from mock import patch
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from capa.tests.response_xml_factory import OptionResponseXMLFactory

from courseware.grades import grade, iterate_grades_for
from courseware.tests.factories import StudentModuleFactory
# from xmodule.modulestore.tests.django_utils import TEST_DATA_MOCK_MODULESTORE
from student.tests.factories import UserFactory, CourseEnrollmentFactory
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.django import modulestore


def _grade_with_errors(student, request, course, keep_raw_scores=False):
    """This fake grade method will throw exceptions for student3 and
    student4, but allow any other students to go through normal grading.

    It's meant to simulate when something goes really wrong while trying to
    grade a particular student, so we can test that we won't kill the entire
    course grading run.
    """
    if student.username in ['student3', 'student4']:
        raise Exception("I don't like {}".format(student.username))

    return grade(student, request, course, keep_raw_scores=keep_raw_scores)

def _create_gradable_problem(course):
    """
    Add problem prepared for grading withing the course
    """
    # add a chapter
    chapter = ItemFactory.create(parent_location=course.location)
    # add a sequence to the course to which the problems can be added
    problem_section = ItemFactory.create(parent_location=chapter.location,
                                         category='sequential',
                                         metadata={'graded': True, 'format': 'Homework'})
    # create problem
    OPTION_1 = 'option 1'
    OPTION_2 = 'option 2'
    PROBLEM_URL_NAME = 'TEST_PROBLEM'

    factory = OptionResponseXMLFactory()
    factory_args = {'question_text': 'The correct answer is {0}'.format(OPTION_1),
                    'options': [OPTION_1, OPTION_2],
                    'correct_option': OPTION_1,
                    'num_responses': 2}
    problem_xml = factory.build_xml(**factory_args)
    problem = ItemFactory.create(parent_location=problem_section.location,
                       parent=problem_section,
                       category="problem",
                       display_name=PROBLEM_URL_NAME,
                       data=problem_xml)
    problem_location = course.id.make_usage_key('problem', PROBLEM_URL_NAME)
    return problem_location

def _prepare_grading_for_student(course, problem_location, student):
    """
    Enroll student for the course and imitate problem access
    """
    CourseEnrollmentFactory.create(course_id=course.id, user=student)
    StudentModuleFactory.create(course_id=course.id,
                                module_state_key=problem_location,
                                student=student,
                                grade=None,
                                max_grade=None,
                                state=None)


# @override_settings(MODULESTORE=TEST_DATA_MOCK_MODULESTORE)
class TestGradingRequest(ModuleStoreTestCase):
    """
    Test correct fake request handling for single student grading
    """
    def setUp(self):
        super(TestGradingRequest, self).setUp()
        self.student = UserFactory.create()
        course = CourseFactory()

        problem_location = _create_gradable_problem(course)
        _prepare_grading_for_student(course, problem_location, self.student)

        # update course for correct get_children() call
        store = modulestore()
        self.course = store.get_course(course.id)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=['127.0.0.1'])
    def test_grading_fail_on_request_with_empty_host(self):
        request = RequestFactory().get('/')
        with self.assertRaises(SuspiciousOperation):
            grade(self.student, request, self.course)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=['127.0.0.1'])
    def test_grading_success_on_request_with_localhost(self):
        request = RequestFactory(HTTP_HOST='127.0.0.1').get('/')
        _grade = grade(self.student, request, self.course)
        self.assertEqual(_grade['percent'], 0.0)


class TestGradeIteration(ModuleStoreTestCase):
    """
    Test iteration through student gradesets.
    """
    COURSE_NUM = "1000"
    COURSE_NAME = "grading_test_course"

    def setUp(self):
        """
        Create a course and a handful of users to assign grades
        """
        super(TestGradeIteration, self).setUp()

        self.course = CourseFactory.create(
            display_name=self.COURSE_NAME,
            number=self.COURSE_NUM
        )
        self.students = [
            UserFactory.create(username='student1'),
            UserFactory.create(username='student2'),
            UserFactory.create(username='student3'),
            UserFactory.create(username='student4'),
            UserFactory.create(username='student5'),
        ]

    def test_empty_student_list(self):
        """If we don't pass in any students, it should return a zero-length
        iterator, but it shouldn't error."""
        gradeset_results = list(iterate_grades_for(self.course.id, []))
        self.assertEqual(gradeset_results, [])

    def test_nonexistent_course(self):
        """If the course we want to get grades for does not exist, a `Http404`
        should be raised. This is a horrible crossing of abstraction boundaries
        and should be fixed, but for now we're just testing the behavior. :-("""
        with self.assertRaises(Http404):
            gradeset_results = iterate_grades_for(SlashSeparatedCourseKey("I", "dont", "exist"), [])
            gradeset_results.next()

    def test_all_empty_grades(self):
        """No students have grade entries"""
        all_gradesets, all_errors = self._gradesets_and_errors_for(self.course.id, self.students)
        self.assertEqual(len(all_errors), 0)
        for gradeset in all_gradesets.values():
            self.assertIsNone(gradeset['grade'])
            self.assertEqual(gradeset['percent'], 0.0)

    @patch('courseware.grades.grade', _grade_with_errors)
    def test_grading_exception(self):
        """Test that we correctly capture exception messages that bubble up from
        grading. Note that we only see errors at this level if the grading
        process for this student fails entirely due to an unexpected event --
        having errors in the problem sets will not trigger this.

        We patch the grade() method with our own, which will generate the errors
        for student3 and student4.
        """
        all_gradesets, all_errors = self._gradesets_and_errors_for(self.course.id, self.students)
        student1, student2, student3, student4, student5 = self.students
        self.assertEqual(
            all_errors,
            {
                student3: "I don't like student3",
                student4: "I don't like student4"
            }
        )

        # But we should still have five gradesets
        self.assertEqual(len(all_gradesets), 5)

        # Even though two will simply be empty
        self.assertFalse(all_gradesets[student3])
        self.assertFalse(all_gradesets[student4])

        # The rest will have grade information in them
        self.assertTrue(all_gradesets[student1])
        self.assertTrue(all_gradesets[student2])
        self.assertTrue(all_gradesets[student5])

    @override_settings(DEBUG=False, ALLOWED_HOSTS=[])
    def test_grading_fail_on_empty_allowed_hosts(self):
        """
        Test usage of RequestFactory with invalid HTTP_HOST for grading
        """
        self._prepare_gradable_problem_for_students()

        all_gradesets, all_errors = self._gradesets_and_errors_for(self.course.id, self.students)
        self.assertFalse(any(all_gradesets.values()))
        self.assertTrue(all(all_errors.values()))

    @override_settings(DEBUG=False, ALLOWED_HOSTS=['127.0.0.1'])
    def test_grading_success_on_allowed_hosts(self):
        """
        Test usage of RequestFactory with valid HTTP_HOST for grading
        """
        self._prepare_gradable_problem_for_students()

        all_gradesets, all_errors = self._gradesets_and_errors_for(self.course.id, self.students)
        self.assertTrue(all(all_gradesets.values()))
        self.assertFalse(any(all_errors.values()))

    ################################# Helpers #################################
    def _gradesets_and_errors_for(self, course_id, students):
        """Simple helper method to iterate through student grades and give us
        two dictionaries -- one that has all students and their respective
        gradesets, and one that has only students that could not be graded and
        their respective error messages."""
        students_to_gradesets = {}
        students_to_errors = {}

        for student, gradeset, err_msg in iterate_grades_for(course_id, students):
            students_to_gradesets[student] = gradeset
            if err_msg:
                students_to_errors[student] = err_msg

        return students_to_gradesets, students_to_errors

    def _prepare_gradable_problem_for_students(self):
        problem_location = _create_gradable_problem(self.course)
        for student in self.students:
            _prepare_grading_for_student(self.course, problem_location, student)
        # update course for correct get_children() call
        store = modulestore()
        self.course = store.get_course(self.course.id)
