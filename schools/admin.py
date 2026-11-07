from django.contrib import admin
from .models import School, ClassRoom, Learner, Teacher, FeeStructure, LearnerFeePayment, Exam, ExamResult, BoardingHouse, BoardingAssignment, BoardingRollCall, UserProfile

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name','code','county','phone','principal','current_term','current_year')
    search_fields = ('name','code','county','phone')

@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ('name','stream','class_teacher_name','capacity')
    list_filter = ('name',)

@admin.register(Learner)
class LearnerAdmin(admin.ModelAdmin):
    list_display = ('admission_no','first_name','last_name','gender','classroom','boarding_type','status','parent1_name','parent1_phone')
    search_fields = ('first_name','last_name','admission_no','parent1_name','parent1_phone','nemis_no')
    list_filter = ('gender','status','boarding_type','classroom')

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('full_name','phone','subject','status','employment_type')
    search_fields = ('full_name','phone','tsc_no')
    list_filter = ('status','employment_type')

@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ('classroom','term','year','total')
    list_filter = ('term','year')

@admin.register(LearnerFeePayment)
class LearnerFeePaymentAdmin(admin.ModelAdmin):
    list_display = ('learner','term','year','amount_paid','method','receipt_no','mpesa_code','date')
    search_fields = ('learner__first_name','learner__last_name','learner__admission_no','receipt_no','mpesa_code')
    list_filter = ('method','term','year')

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('name','term','year','classroom')

@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ('learner','subject','score','term','year')
    search_fields = ('learner__first_name','learner__admission_no','subject')
    list_filter = ('term','year','subject')

@admin.register(BoardingHouse)
class BoardingHouseAdmin(admin.ModelAdmin):
    list_display = ('name','gender','capacity','matron_patron','matron_phone')
    list_filter = ('gender',)

@admin.register(BoardingAssignment)
class BoardingAssignmentAdmin(admin.ModelAdmin):
    list_display = ('learner','house','bed_no','status','boarding_fee_expected','boarding_fee_paid')
    search_fields = ('learner__first_name','learner__admission_no','house__name')
    list_filter = ('status','house')

@admin.register(BoardingRollCall)
class BoardingRollCallAdmin(admin.ModelAdmin):
    list_display = ('assignment','date','present')
    list_filter = ('present','date')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user','role','phone','learner')
    search_fields = ('user__username','phone')
    list_filter = ('role',)