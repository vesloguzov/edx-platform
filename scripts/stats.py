# coding=utf-8
from dj_lms import *

import os
import sys
import glob
import datetime

from django.utils.timezone import UTC
from django.db.models import Count

from xmodule.modulestore.django import modulestore

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from student.models import CourseEnrollment


OVERALL_SUMMARY_DAY_LIMIT = 10


def main(dirname):
    # remove old per-course stats
    for filename in glob.glob(os.path.join(dirname, 'enrollment-*.xml.xls')):
        os.remove(filename)

    courses = [
        c for c in CourseOverview.objects.all()
        if not c.has_ended()
        and c.enrollment_start and c.enrollment_start < datetime.datetime.now(UTC())
        and not is_utility_course(c)
    ]
    courses = sorted(courses, key=lambda c: c.display_name)

    all_enrollments = {}
    for course in courses:
        enrollments = CourseEnrollment.objects.filter(course_id=course.id, is_active=True).order_by('created')
        enrollments = enrollments.values_list('created', flat=True)
        all_enrollments[course.id] = enrollments

    reports = {}
    for course in courses:
        report_filename = 'enrollment-{}.xml.xls'.format(unicode(course.id).replace('/', '-').replace(':', '-'))
        with open(os.path.join(dirname, report_filename), 'w') as course_summary:
            write_report(course_summary, all_enrollments, course)
        reports[course.id] = report_filename

    with open(os.path.join(dirname, 'short-enrollment-summary.html'), 'w') as short_summary:
        write_summary(short_summary, all_enrollments, courses, reports)


def is_utility_course(course):
    run = course.id.run.lower()
    return 'demo' in run or 'preview' in run


def write_summary(f, all_enrollments, courses, reports):
    items = []
    for course in courses:
        enrollments = list(all_enrollments[course.id])
        total = len(enrollments)
        today = len([enrollment for enrollment in enrollments
                    if enrollment.date() == datetime.date.today()])
        items.append(COURSE_HTML.format(
            course=u'{} ({})'.format(course.display_name, course.id),
            today=today,
            total=total,
            filename=reports[course.id]
        ))

    summary = u'</tr><tr>'.join(
        u'<td>{}</td><td style="text-align: right">{}</td>'.format(date.strftime('%d-%m-%y'), count)
        for date, count in overall_summary(all_enrollments)
    )
    content = HTML.format(summary, u''.join(items)).encode('utf-8')
    f.write(content)


def write_report(f, all_enrollments, course):
    enrollments = all_enrollments[course.id]
    aggregated_enrollements = stats_per_day(enrollments)
    per_day_items = []
    prev_count = 0

    for date, count in aggregated_enrollements:
        diff = count - prev_count
        item = XML_XLS_ROW.format(
            date=date.strftime('%d-%m-%y'),
            count=count,
            diff='%+d' % diff if diff != 0 else '='
        )
        prev_count = count
        per_day_items.append(item)

    per_day_items.append(XML_XLS_ROW.format(
        date=u'ВСЕГО',
        count=len(enrollments),
        diff=''
    ))
    sheet = XML_XLS_SHEET.format(
        sheet_name='Enrollment summary',
        course_name=u'{} ({})'.format(course.display_name, course.id),
        rows=u''.join(per_day_items)
    )

    result = XML_XLS.format(sheet=sheet)
    f.write(result.encode('utf-8'))


def stats_per_day(enrollment_datetimes, start=None):
    start = start or enrollment_datetimes[0].date()
    days_count = (datetime.date.today() - start).days
    dates = [start + datetime.timedelta(days=i) for i in range(days_count + 1)]
    result = []
    for date in dates:
        result.append((date, sum(1 for dt in enrollment_datetimes if dt.date() == date)))
    return result


def overall_summary(all_enrollments):
    start = datetime.date.today() - datetime.timedelta(days=OVERALL_SUMMARY_DAY_LIMIT)
    enrollments = sorted(sum(
        (list(enrollments.filter(created__gte=start)) for enrollments in all_enrollments.values()),
        []
    ))
    enrollments = [d for d in enrollments if d.date() >= start]
    return reversed(stats_per_day(enrollments, start))


HTML = u'<!DOCTYPE html><html><head><title>Enrollment statistics</title><meta charset="UTF-8"></head><body><table><tr><th>Дата</th><th>Количество<br>записавшихся</th></tr><tr>{}</tr></table>{}<p></p></body></html>'
COURSE_HTML = u'<p><strong>{course}</strong>:<br>Сегодня: {today}<br>Всего: {total}<br><a href="{filename}">Подробнее...</a></p>'

XML_XLS = u'''\
<?xml version="1.0"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:html="http://www.w3.org/TR/REC-html40">
 <DocumentProperties xmlns="urn:schemas-microsoft-com:office:office">
  <Author>Lektorium</Author>
  <Company>Lektorium</Company>
  <Version>1.0</Version>
 </DocumentProperties>
 <ExcelWorkbook xmlns="urn:schemas-microsoft-com:office:excel">
  <ActiveSheet>1</ActiveSheet>
 </ExcelWorkbook>
 <Styles>
  <Style ss:ID="Default">
   <ss:Borders>
    <ss:Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#dddddd" />
    <ss:Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#dddddd" />
    <ss:Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#dddddd" />
    <ss:Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#dddddd" />
   </ss:Borders>
   <ss:NumberFormat ss:Format="General" />
   <Font ss:Size="9"/>
  </Style>

  <Style ss:ID="Header">
   <Font ss:Bold="1"/>
   <ss:Borders>
    <ss:Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#dddddd" />
    <ss:Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000" />
    <ss:Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#dddddd" />
    <ss:Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#dddddd" />
   </ss:Borders>
  </Style>
 </Styles>
 {sheet}
</Workbook>'''

XML_XLS_SHEET = u'''
 <Worksheet ss:Name="{sheet_name}">
  <Table ss:DefaultColumnWidth="75">
   <Column/>
   <Column ss:Width="80"/>
   <Column ss:Width="80"/>
   <Column ss:Width="100"/>
   <Column/>

   <Row>
    <Cell ss:StyleID="Header" ss:MergeAcross="2"><Data ss:Type="String">{course_name}</Data></Cell>
   </Row>
   <Row>
    <Cell><Data ss:Type="String">Дата</Data></Cell>
    <Cell><Data ss:Type="String">Кол-во записавшихся</Data></Cell>
    <Cell><Data ss:Type="String">Динамика</Data></Cell>
   </Row>
   {rows}
  </Table>
  <x:WorksheetOptions xmlns:x="urn:schemas-microsoft-com:office:excel">
   <x:PageSetup>
    <x:Layout x:Orientation="Landscape"/>
    <x:PageMargins x:Bottom="0.98425196850393704" x:Left="0.39370078740157483" x:Right="0.39370078740157483" x:Top="0.98425196850393704"/>
    <x:Header x:Data="&amp;LLektorium&#10;&amp;&quot;Arial,Bold&quot;&amp;11"  x:Margin="0.39370078740157483"/>
   </x:PageSetup>
  </x:WorksheetOptions>
 </Worksheet>
'''
XML_XLS_ROW = u'''
   <Row>
    <Cell><Data ss:Type="String">{date}</Data></Cell>
    <Cell><Data ss:Type="Number">{count}</Data></Cell>
    <Cell><Data ss:Type="String">{diff}</Data></Cell>
   </Row>
'''

if __name__ == '__main__':
    main(sys.argv[1])
