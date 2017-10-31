"""
Test grade calculation.
"""

import datetime
import itertools

import ddt
from mock import patch, PropertyMock, MagicMock
from nose.plugins.attrib import attr

from capa.tests.response_xml_factory import MultipleChoiceResponseXMLFactory
from lms.djangoapps.course_blocks.api import get_course_blocks
from openedx.core.djangoapps.content.block_structure.factory import BlockStructureFactory
from openedx.core.djangolib.testing.utils import get_mock_request
from student.models import CourseEnrollment
from student.tests.factories import UserFactory
from xmodule.graders import ProblemScore
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory

from ..new.course_grade_factory import CourseGradeFactory
from ..new.subsection_grade_factory import SubsectionGradeFactory
from .utils import answer_problem


@attr(shard=1)
class TestGradeIteration(SharedModuleStoreTestCase):
    """
    Test iteration through student course grades.
    """
    COURSE_NUM = "1000"
    COURSE_NAME = "grading_test_course"

    @classmethod
    def setUpClass(cls):
        super(TestGradeIteration, cls).setUpClass()
        cls.course = CourseFactory.create(
            display_name=cls.COURSE_NAME,
            number=cls.COURSE_NUM
        )

    def setUp(self):
        """
        Create a course and a handful of users to assign grades
        """
        super(TestGradeIteration, self).setUp()

        self.students = [
            UserFactory.create(username='student1'),
            UserFactory.create(username='student2'),
            UserFactory.create(username='student3'),
            UserFactory.create(username='student4'),
            UserFactory.create(username='student5'),
        ]

    def test_empty_student_list(self):
        """
        If we don't pass in any students, it should return a zero-length
        iterator, but it shouldn't error.
        """
        grade_results = list(CourseGradeFactory().iter([], self.course))
        self.assertEqual(grade_results, [])

    def test_all_empty_grades(self):
        """
        No students have grade entries.
        """
        with patch.object(
            BlockStructureFactory,
            'create_from_store',
            wraps=BlockStructureFactory.create_from_store
        ) as mock_create_from_store:
            all_course_grades, all_errors = self._course_grades_and_errors_for(self.course, self.students)
            self.assertEquals(mock_create_from_store.call_count, 1)

        self.assertEqual(len(all_errors), 0)
        for course_grade in all_course_grades.values():
            self.assertIsNone(course_grade.letter_grade)
            self.assertEqual(course_grade.percent, 0.0)

    @patch('lms.djangoapps.grades.new.course_grade_factory.CourseGradeFactory.create')
    def test_grading_exception(self, mock_course_grade):
        """Test that we correctly capture exception messages that bubble up from
        grading. Note that we only see errors at this level if the grading
        process for this student fails entirely due to an unexpected event --
        having errors in the problem sets will not trigger this.

        We patch the grade() method with our own, which will generate the errors
        for student3 and student4.
        """

        student1, student2, student3, student4, student5 = self.students
        mock_course_grade.side_effect = [
            Exception("Error for {}.".format(student.username))
            if student.username in ['student3', 'student4']
            else mock_course_grade.return_value
            for student in self.students
        ]
        with self.assertNumQueries(4):
            all_course_grades, all_errors = self._course_grades_and_errors_for(self.course, self.students)
        self.assertEqual(
            {student: all_errors[student].message for student in all_errors},
            {
                student3: "Error for student3.",
                student4: "Error for student4.",
            }
        )

        # But we should still have five gradesets
        self.assertEqual(len(all_course_grades), 5)

        # Even though two will simply be empty
        self.assertIsNone(all_course_grades[student3])
        self.assertIsNone(all_course_grades[student4])

        # The rest will have grade information in them
        self.assertIsNotNone(all_course_grades[student1])
        self.assertIsNotNone(all_course_grades[student2])
        self.assertIsNotNone(all_course_grades[student5])

    def _course_grades_and_errors_for(self, course, students):
        """
        Simple helper method to iterate through student grades and give us
        two dictionaries -- one that has all students and their respective
        course grades, and one that has only students that could not be graded
        and their respective error messages.
        """
        students_to_course_grades = {}
        students_to_errors = {}

        for student, course_grade, error in CourseGradeFactory().iter(students, course):
            students_to_course_grades[student] = course_grade
            if error:
                students_to_errors[student] = error

        return students_to_course_grades, students_to_errors


@ddt.ddt
class TestWeightedProblems(SharedModuleStoreTestCase):
    """
    Test scores and grades with various problem weight values.
    """
    @classmethod
    def setUpClass(cls):
        super(TestWeightedProblems, cls).setUpClass()
        cls.course = CourseFactory.create()
        with cls.store.bulk_operations(cls.course.id):
            cls.chapter = ItemFactory.create(parent=cls.course, category="chapter", display_name="chapter")
            cls.sequential = ItemFactory.create(parent=cls.chapter, category="sequential", display_name="sequential")
            cls.vertical = ItemFactory.create(parent=cls.sequential, category="vertical", display_name="vertical1")
            problem_xml = cls._create_problem_xml()
            cls.problems = []
            for i in range(2):
                cls.problems.append(
                    ItemFactory.create(
                        parent=cls.vertical,
                        category="problem",
                        display_name="problem_{}".format(i),
                        data=problem_xml,
                    )
                )

    def setUp(self):
        super(TestWeightedProblems, self).setUp()
        self.user = UserFactory()
        self.request = get_mock_request(self.user)

    @classmethod
    def _create_problem_xml(cls):
        """
        Creates and returns XML for a multiple choice response problem
        """
        return MultipleChoiceResponseXMLFactory().build_xml(
            question_text='The correct answer is Choice 3',
            choices=[False, False, True, False],
            choice_names=['choice_0', 'choice_1', 'choice_2', 'choice_3']
        )

    def _verify_grades(self, raw_earned, raw_possible, weight, expected_score):
        """
        Verifies the computed grades are as expected.
        """
        with self.store.branch_setting(ModuleStoreEnum.Branch.draft_preferred):
            # pylint: disable=no-member
            for problem in self.problems:
                problem.weight = weight
                self.store.update_item(problem, self.user.id)
            self.store.publish(self.course.location, self.user.id)

        course_structure = get_course_blocks(self.request.user, self.course.location)

        # answer all problems
        for problem in self.problems:
            answer_problem(self.course, self.request, problem, score=raw_earned, max_value=raw_possible)

        # get grade
        subsection_grade = SubsectionGradeFactory(
            self.request.user, self.course, course_structure
        ).update(self.sequential)

        # verify all problem grades
        for problem in self.problems:
            problem_score = subsection_grade.problem_scores[problem.location]
            self.assertEqual(type(expected_score.first_attempted), type(problem_score.first_attempted))
            expected_score.first_attempted = problem_score.first_attempted
            self.assertEquals(problem_score, expected_score)

        # verify subsection grades
        self.assertEquals(subsection_grade.all_total.earned, expected_score.earned * len(self.problems))
        self.assertEquals(subsection_grade.all_total.possible, expected_score.possible * len(self.problems))

    @ddt.data(
        *itertools.product(
            (0.0, 0.5, 1.0, 2.0),  # raw_earned
            (-2.0, -1.0, 0.0, 0.5, 1.0, 2.0),  # raw_possible
            (-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 50.0, None),  # weight
        )
    )
    @ddt.unpack
    def test_problem_weight(self, raw_earned, raw_possible, weight):

        use_weight = weight is not None and raw_possible != 0
        if use_weight:
            expected_w_earned = raw_earned / raw_possible * weight
            expected_w_possible = weight
        else:
            expected_w_earned = raw_earned
            expected_w_possible = raw_possible

        expected_graded = expected_w_possible > 0

        expected_score = ProblemScore(
            raw_earned=raw_earned,
            raw_possible=raw_possible,
            weighted_earned=expected_w_earned,
            weighted_possible=expected_w_possible,
            weight=weight,
            graded=expected_graded,
            first_attempted=datetime.datetime(2010, 1, 1),
        )
        self._verify_grades(raw_earned, raw_possible, weight, expected_score)


class TestScoreForModule(SharedModuleStoreTestCase):
    """
    Test the method that calculates the score for a given block based on the
    cumulative scores of its children. This test class uses a hard-coded block
    hierarchy with scores as follows:
                                                a
                                       +--------+--------+
                                       b                 c
                        +--------------+-----------+     |
                        d              e           f     g
                     +-----+     +-----+-----+     |     |
                     h     i     j     k     l     m     n
                   (2/5) (3/5) (0/1)   -   (1/3)   -   (3/10)

    """
    @classmethod
    def setUpClass(cls):
        super(TestScoreForModule, cls).setUpClass()
        cls.course = CourseFactory.create()
        with cls.store.bulk_operations(cls.course.id):
            cls.a = ItemFactory.create(parent=cls.course, category="chapter", display_name="a")
            cls.b = ItemFactory.create(parent=cls.a, category="sequential", display_name="b")
            cls.c = ItemFactory.create(parent=cls.a, category="sequential", display_name="c")
            cls.d = ItemFactory.create(parent=cls.b, category="vertical", display_name="d")
            cls.e = ItemFactory.create(parent=cls.b, category="vertical", display_name="e")
            cls.f = ItemFactory.create(parent=cls.b, category="vertical", display_name="f")
            cls.g = ItemFactory.create(parent=cls.c, category="vertical", display_name="g")
            cls.h = ItemFactory.create(parent=cls.d, category="problem", display_name="h")
            cls.i = ItemFactory.create(parent=cls.d, category="problem", display_name="i")
            cls.j = ItemFactory.create(parent=cls.e, category="problem", display_name="j")
            cls.k = ItemFactory.create(parent=cls.e, category="html", display_name="k")
            cls.l = ItemFactory.create(parent=cls.e, category="problem", display_name="l")
            cls.m = ItemFactory.create(parent=cls.f, category="html", display_name="m")
            cls.n = ItemFactory.create(parent=cls.g, category="problem", display_name="n")

        cls.request = get_mock_request(UserFactory())
        CourseEnrollment.enroll(cls.request.user, cls.course.id)

        answer_problem(cls.course, cls.request, cls.h, score=2, max_value=5)
        answer_problem(cls.course, cls.request, cls.i, score=3, max_value=5)
        answer_problem(cls.course, cls.request, cls.j, score=0, max_value=1)
        answer_problem(cls.course, cls.request, cls.l, score=1, max_value=3)
        answer_problem(cls.course, cls.request, cls.n, score=3, max_value=10)

        cls.course_grade = CourseGradeFactory().create(cls.request.user, cls.course)

    def test_score_chapter(self):
        earned, possible = self.course_grade.score_for_module(self.a.location)
        self.assertEqual(earned, 9)
        self.assertEqual(possible, 24)

    def test_score_section_many_leaves(self):
        earned, possible = self.course_grade.score_for_module(self.b.location)
        self.assertEqual(earned, 6)
        self.assertEqual(possible, 14)

    def test_score_section_one_leaf(self):
        earned, possible = self.course_grade.score_for_module(self.c.location)
        self.assertEqual(earned, 3)
        self.assertEqual(possible, 10)

    def test_score_vertical_two_leaves(self):
        earned, possible = self.course_grade.score_for_module(self.d.location)
        self.assertEqual(earned, 5)
        self.assertEqual(possible, 10)

    def test_score_vertical_two_leaves_one_unscored(self):
        earned, possible = self.course_grade.score_for_module(self.e.location)
        self.assertEqual(earned, 1)
        self.assertEqual(possible, 4)

    def test_score_vertical_no_score(self):
        earned, possible = self.course_grade.score_for_module(self.f.location)
        self.assertEqual(earned, 0)
        self.assertEqual(possible, 0)

    def test_score_vertical_one_leaf(self):
        earned, possible = self.course_grade.score_for_module(self.g.location)
        self.assertEqual(earned, 3)
        self.assertEqual(possible, 10)

    def test_score_leaf(self):
        earned, possible = self.course_grade.score_for_module(self.h.location)
        self.assertEqual(earned, 2)
        self.assertEqual(possible, 5)

    def test_score_leaf_no_score(self):
        earned, possible = self.course_grade.score_for_module(self.m.location)
        self.assertEqual(earned, 0)
        self.assertEqual(possible, 0)


@attr(shard=1)
class GradeDistinctionTest(SharedModuleStoreTestCase):
    """
    Test computing of final course grade
    """
    GRADE_CUTOFFS = {'A': 0.9, 'B': 0.6}

    def setUp(self):
        """
        Create a course and a user to assign grades
        """
        super(GradeDistinctionTest, self).setUp()

        self.course = CourseFactory.create(
            grade_cutoffs = self.GRADE_CUTOFFS
        )
        self.course = self.store.get_course(self.course.id)
        self.student = UserFactory.create()
        CourseEnrollment.enroll(self.student, self.course.id)

    def test_grade_with_distinction(self):
        """
        Test the result of grading includes "distinction" item set to True
        if student gets grade over largest grade cutoff
        """
        with patch('xmodule.course_module.CourseDescriptor.grader', PropertyMock) as mock_grader:
            mock_grader.grade = MagicMock(return_value={'percent': 0.95})

            course_grade = CourseGradeFactory().create(self.student, self.course)
            self.assertTrue(hasattr(course_grade, 'distinction'))
            self.assertTrue(course_grade.distinction, 'The distinction is not calculated correctly')

    def test_grade_no_distinction(self):
        """
        Test the result of grading includes "distinction" item set to False
        if student gets grade under largest grade cutoff
        """
        with patch('xmodule.course_module.CourseDescriptor.grader', PropertyMock) as mock_grader:
            mock_grader.grade = MagicMock(return_value={'percent': 0.75})

            course_grade = CourseGradeFactory().create(self.student, self.course)
            self.assertTrue(hasattr(course_grade, 'distinction'))
            self.assertFalse(course_grade.distinction, 'The distinction is not calculated correctly')
