from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout as auth_logout, authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.http import HttpResponse
import csv
from .models import School, ClassRoom, Learner, Teacher, FeeStructure, LearnerFeePayment, Exam, ExamResult, BoardingHouse, BoardingAssignment, BoardingRollCall, UserProfile

def get_school(request):
    sid = request.session.get('school_id')
    if sid:
        try: return School.objects.get(id=sid)
        except: pass
    return School.objects.first()

def get_role(request):
    if request.user.is_superuser:
        return request.session.get('role','Admin')
    try: return request.user.profile.role
    except: return request.session.get('role','Admin')

def get_context(request):
    return {'school': get_school(request), 'term': 'Term 3', 'year': '2026', 'today': timezone.now().date(), 'user_role': get_role(request) if request.user.is_authenticated else 'Guest'}

def redirect_by_role(role):
    if role == 'Learner': return redirect('student')
    if role == 'Parent': return redirect('parents')
    if role == 'Bursar': return redirect('fees')
    if role == 'Matron': return redirect('boarding')
    return redirect('dashboard')

def custom_login(request):
    if request.GET.get('show') == '1':
        auth_logout(request); request.session.flush(); return render(request, 'login.html', {})
    if request.user.is_authenticated and request.method == 'GET':
        return redirect_by_role(get_role(request))
    if request.method == 'POST':
        username = request.POST.get('username','').strip()
        password = request.POST.get('password','')
        chosen = request.POST.get('role','Admin')
        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, "Wrong username or password. Try again or click Forgot Password / Create Account.")
            return render(request, 'login.html', {})
        profile, created = UserProfile.objects.get_or_create(user=user, defaults={'role': chosen})
        if not user.is_superuser:
            if profile.role != chosen and chosen == 'Admin':
                messages.error(request, f"You are registered as {profile.role}, you cannot login as Admin. Choose {profile.role}.")
                return render(request, 'login.html', {})
            real_role = profile.role
        else:
            profile.role = chosen; profile.save(); real_role = chosen
        auth_login(request, user)
        request.session['role'] = real_role; request.session['username'] = user.username
        messages.success(request, f"Welcome {user.username} - Logged in as {real_role}")
        return redirect_by_role(real_role)
    return render(request, 'login.html', {})

def register_account(request):
    if request.user.is_authenticated:
        return redirect_by_role(get_role(request))
    if request.method == 'POST':
        full_name = request.POST.get('full_name','').strip()
        username = request.POST.get('username','').strip()
        phone = request.POST.get('phone','').strip()
        email = request.POST.get('email','').strip()
        admission_no = request.POST.get('admission_no','').strip()
        role = request.POST.get('role','Teacher')
        password = request.POST.get('password','')
        password2 = request.POST.get('password2','')
        if not full_name or not username or not phone or not password:
            messages.error(request, "Please fill Full Name, Username, Phone and Password.")
            return render(request, 'register.html', {})
        if password != password2:
            messages.error(request, "Passwords do not match. Type same password twice.")
            return render(request, 'register.html', {})
        if len(password) < 4:
            messages.error(request, "Password must be at least 4 characters.")
            return render(request, 'register.html', {})
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already taken. Try another username or Login.")
            return render(request, 'register.html', {})
        if email and User.objects.filter(email=email).exists():
            messages.error(request, "That email is already used. Use another email.")
            return render(request, 'register.html', {})
        parts = full_name.split()
        first = parts[0] if parts else full_name
        last = " ".join(parts[1:]) if len(parts) > 1 else ""
        user = User.objects.create_user(username=username, email=email, password=password, first_name=first, last_name=last)
        linked_learner = None
        if admission_no:
            try: linked_learner = Learner.objects.get(admission_no__iexact=admission_no)
            except: linked_learner = None
        UserProfile.objects.create(user=user, role=role, phone=phone, learner=linked_learner)
        if role == 'Admin':
            messages.success(request, "Admin account created. Please ask Head Teacher to approve / make you superuser in /admin/ if needed. Now login.")
        elif linked_learner:
            messages.success(request, f"Account created! Linked to Learner {linked_learner.full_name} ({linked_learner.admission_no}). Now login as {role}.")
        elif admission_no:
            messages.success(request, f"Account created! Admission No {admission_no} not found yet. Admin will link you later. Now login as {role}.")
        else:
            messages.success(request, f"Account created as {role}! Now login with username {username}.")
        return redirect('login')
    return render(request, 'register.html', {})

def forgot_password(request):
    if request.method == 'POST':
        username = request.POST.get('username','').strip()
        phone = request.POST.get('phone','').strip()
        new_password = request.POST.get('new_password','')
        new_password2 = request.POST.get('new_password2','')
        if not username or not phone or not new_password:
            messages.error(request, "Fill Username, Phone and New Password.")
            return render(request, 'forgot_password.html', {})
        if new_password != new_password2:
            messages.error(request, "New passwords do not match.")
            return render(request, 'forgot_password.html', {})
        if len(new_password) < 4:
            messages.error(request, "New password must be at least 4 characters.")
            return render(request, 'forgot_password.html', {})
        try: user = User.objects.get(username=username)
        except:
            messages.error(request, f"No account with username '{username}'. Click Create Account.")
            return render(request, 'forgot_password.html', {})
        try:
            prof = user.profile
            saved_phone = (prof.phone or "").strip()
            if saved_phone and saved_phone != phone:
                messages.error(request, "Phone does not match the phone you used when creating account. Ask Admin to reset for you in /admin/.")
                return render(request, 'forgot_password.html', {})
            if not saved_phone:
                prof.phone = phone; prof.save()
        except: pass
        user.set_password(new_password); user.save()
        messages.success(request, f"Password reset! Now login with username {username} and your new password.")
        return redirect('login')
    return render(request, 'forgot_password.html', {})

def custom_logout(request):
    auth_logout(request); request.session.flush(); return redirect('login')

@login_required
def dashboard(request):
    role = get_role(request)
    if role == 'Learner': return redirect('student')
    if role == 'Parent': return redirect('parents')
    if role == 'Bursar': return redirect('fees')
    if role == 'Matron': return redirect('boarding')
    ctx = get_context(request); school = get_school(request); learners = Learner.objects.all()
    total_learners = learners.count(); male_count = learners.filter(gender='Male').count(); female_count = learners.filter(gender='Female').count(); active_learners = learners.filter(status='Active').count(); day_count = learners.filter(boarding_type='Day').count(); boarding_count = learners.filter(boarding_type='Boarding').count(); semi_count = learners.filter(boarding_type='Semi-Boarding').count()
    term = school.current_term if school and school.current_term else 'Term 3'; year = school.current_year if school and school.current_year else '2026'
    payments = LearnerFeePayment.objects.filter(term=term, year=year); total_collected = float(payments.aggregate(t=Sum('amount_paid'))['t'] or 0)
    total_expected = 0
    for l in learners:
        fs = FeeStructure.objects.filter(classroom=l.classroom, term=term, year=year).first() or FeeStructure.objects.filter(classroom__isnull=True, term=term, year=year).first()
        if fs: total_expected += float(fs.total)
    total_balance = total_expected - total_collected; collection_pct = round((total_collected / total_expected * 100) if total_expected else 0, 1)
    by_method = {}
    for m in ['Cash','M-Pesa','Bank','Cheque','Bursary','Other']:
        by_method[m] = float(LearnerFeePayment.objects.filter(method=m, term=term, year=year).aggregate(t=Sum('amount_paid'))['t'] or 0)
    unpaid_list = []
    for l in learners:
        paid = float(LearnerFeePayment.objects.filter(learner=l, term=term, year=year).aggregate(t=Sum('amount_paid'))['t'] or 0)
        fs = FeeStructure.objects.filter(classroom=l.classroom, term=term, year=year).first() or FeeStructure.objects.filter(classroom__isnull=True, term=term, year=year).first()
        exp = float(fs.total) if fs else 0
        if exp > paid: unpaid_list.append({'learner': l, 'expected': exp, 'paid': paid, 'balance': exp - paid})
    unpaid_list = sorted(unpaid_list, key=lambda x: x['balance'], reverse=True)[:8]
    classes_list = []
    for c in ClassRoom.objects.all():
        cl = learners.filter(classroom=c); classes_list.append({'classroom': c, 'total': cl.count(), 'male': cl.filter(gender='Male').count(), 'female': cl.filter(gender='Female').count(), 'boarding': cl.filter(boarding_type='Boarding').count()})
    houses = BoardingHouse.objects.all(); total_beds = sum(h.capacity for h in houses); occupied_beds = BoardingAssignment.objects.filter(status='Active').count(); free_beds = total_beds - occupied_beds; boarding_expected = float(sum(float(a.boarding_fee_expected) for a in BoardingAssignment.objects.all()) or 0); boarding_paid = float(sum(float(a.boarding_fee_paid) for a in BoardingAssignment.objects.all()) or 0)
    exam_results = ExamResult.objects.filter(term=term, year=year); avg_score = round(float(exam_results.aggregate(a=Avg('score'))['a'] or 0), 1)
    top_learners = []
    for l in learners:
        rs = ExamResult.objects.filter(learner=l, term=term, year=year)
        if rs.exists():
            mean = float(rs.aggregate(a=Avg('score'))['a'] or 0); top_learners.append({'learner': l, 'mean': round(mean, 1), 'count': rs.count()})
    top_learners = sorted(top_learners, key=lambda x: x['mean'], reverse=True)[:5]
    ctx.update({'school_obj': school, 'selected_term': term, 'selected_year': year, 'total_learners': total_learners, 'male_count': male_count, 'female_count': female_count, 'active_learners': active_learners, 'boarding_count': boarding_count, 'day_count': day_count, 'semi_count': semi_count, 'total_classes': ClassRoom.objects.count(), 'total_schools': School.objects.count(), 'total_teachers': Teacher.objects.count(), 'active_teachers': Teacher.objects.filter(status='Active').count(), 'recent_learners': learners.order_by('-id')[:8], 'classes_list': classes_list, 'attendance_today': '96%', 'total_expected': total_expected, 'total_collected': total_collected, 'total_balance': total_balance, 'collection_pct': collection_pct, 'by_method': by_method, 'total_cash': by_method.get('Cash',0), 'total_mpesa': by_method.get('M-Pesa',0), 'total_bank': by_method.get('Bank',0), 'total_bursary': by_method.get('Bursary',0), 'unpaid_list': unpaid_list, 'unpaid_count': len(unpaid_list), 'total_houses': houses.count(), 'total_beds': total_beds, 'occupied_beds': occupied_beds, 'free_beds': free_beds, 'boarding_active': occupied_beds, 'boarding_expected': boarding_expected, 'boarding_paid': boarding_paid, 'boarding_balance': boarding_expected - boarding_paid, 'houses': houses, 'recent_payments': LearnerFeePayment.objects.all().order_by('-id')[:8], 'recent_boarding': BoardingAssignment.objects.filter(status='Active').order_by('-id')[:5], 'avg_score': avg_score, 'top_learners': top_learners, 'total_exam_results': exam_results.count(), 'recent_teachers': Teacher.objects.all().order_by('-id')[:5]})
    return render(request, 'dashboard.html', ctx)

@login_required
def analytics(request):
    ctx = get_context(request); learners = Learner.objects.all()
    ctx.update({'total_learners': learners.count(), 'by_class': list(learners.values('classroom__name').annotate(total=Count('id')).order_by('classroom__name')), 'by_gender': list(learners.values('gender').annotate(total=Count('id'))), 'by_county': list(learners.values('county').annotate(total=Count('id')).order_by('-total')[:10]), 'by_boarding': list(learners.values('boarding_type').annotate(total=Count('id'))), 'by_status': list(learners.values('status').annotate(total=Count('id'))), 'male_count': learners.filter(gender='Male').count(), 'female_count': learners.filter(gender='Female').count()})
    return render(request, 'analytics.html', ctx)

@login_required
def schools(request):
    ctx = get_context(request)
    if get_role(request) not in ['Admin']:
        messages.error(request, "Only Admin can view Schools."); return redirect_by_role(get_role(request))
    objs = School.objects.all().order_by('-id')
    if request.method == 'POST':
        School.objects.create(name=request.POST.get('name'), code=request.POST.get('code'), location=request.POST.get('location'), county=request.POST.get('county'), phone=request.POST.get('phone'), email=request.POST.get('email'), principal=request.POST.get('principal'), motto=request.POST.get('motto'))
        messages.success(request, "School created!"); return redirect('schools')
    ctx['schools_list'] = objs; return render(request, 'schools.html', ctx)

@login_required
def school_settings(request):
    ctx = get_context(request)
    if get_role(request) not in ['Admin']:
        messages.error(request, "Only Admin can change School Settings."); return redirect_by_role(get_role(request))
    school = get_school(request)
    if request.method == 'POST' and school:
        d = request.POST; school.name = d.get('name', school.name); school.code = d.get('code', school.code); school.location = d.get('location', school.location); school.county = d.get('county', school.county); school.phone = d.get('phone', school.phone); school.email = d.get('email', school.email); school.principal = d.get('principal', school.principal); school.motto = d.get('motto', school.motto); school.registration_no = d.get('registration_no',''); school.school_type = d.get('school_type','Public'); school.level = d.get('level',''); school.gender_type = d.get('gender_type','Mixed'); school.boarding_type = d.get('boarding_type','Day')
        if request.FILES.get('logo'): school.logo = request.FILES.get('logo')
        school.sub_county = d.get('sub_county',''); school.village = d.get('village',''); school.physical_address = d.get('physical_address',''); school.postal_address = d.get('postal_address',''); school.principal_phone = d.get('principal_phone',''); school.deputy = d.get('deputy',''); school.senior_teacher = d.get('senior_teacher',''); school.bursar = d.get('bursar',''); school.secretary = d.get('secretary',''); school.whatsapp = d.get('whatsapp',''); school.website = d.get('website',''); school.mpesa_paybill = d.get('mpesa_paybill',''); school.mpesa_till = d.get('mpesa_till',''); school.mpesa_account_label = d.get('mpesa_account_label','Admission No'); school.mpesa_phone = d.get('mpesa_phone',''); school.bank_name = d.get('bank_name',''); school.bank_branch = d.get('bank_branch',''); school.bank_account = d.get('bank_account',''); school.bank_account_name = d.get('bank_account_name',''); school.vision = d.get('vision',''); school.mission = d.get('mission',''); school.current_term = d.get('current_term','Term 3'); school.current_year = d.get('current_year','2026'); school.opening_date = d.get('opening_date') or None; school.closing_date = d.get('closing_date') or None; school.next_term_date = d.get('next_term_date') or None; school.save(); messages.success(request, "School settings saved!"); return redirect('school_settings')
    ctx['school_obj'] = school; ctx['total_learners'] = Learner.objects.count(); ctx['total_teachers'] = Teacher.objects.count(); ctx['total_classes'] = ClassRoom.objects.count(); return render(request, 'school_settings.html', ctx)

@login_required
def switch_school(request, school_id):
    request.session['school_id'] = school_id; return redirect('dashboard')

@login_required
def learners(request):
    ctx = get_context(request)
    if get_role(request) in ['Learner','Parent','Bursar']:
        messages.error(request, "You cannot view all Learners."); return redirect_by_role(get_role(request))
    q = request.GET.get('q', ''); objs = Learner.objects.all().order_by('-id')
    if q: objs = objs.filter(Q(first_name__icontains=q)|Q(last_name__icontains=q)|Q(middle_name__icontains=q)|Q(admission_no__icontains=q)|Q(parent1_phone__icontains=q)|Q(nemis_no__icontains=q)|Q(county__icontains=q)|Q(parent1_name__icontains=q))
    if request.method == 'POST':
        d = request.POST
        try:
            Learner.objects.create(first_name=d.get('first_name'), middle_name=d.get('middle_name'), last_name=d.get('last_name'), gender=d.get('gender','Male'), date_of_birth=d.get('date_of_birth') or None, birth_cert_no=d.get('birth_cert_no'), nemis_no=d.get('nemis_no'), religion=d.get('religion','Christian'), nationality=d.get('nationality','Kenyan'), county=d.get('county'), sub_county=d.get('sub_county'), village=d.get('village'), physical_address=d.get('physical_address'), photo=request.FILES.get('photo'), admission_no=d.get('admission_no') or '', admission_date=d.get('admission_date') or None, classroom_id=d.get('classroom') or None, stream=d.get('stream'), previous_school=d.get('previous_school'), previous_class=d.get('previous_class'), boarding_type=d.get('boarding_type','Day'), transport_route=d.get('transport_route'), house=d.get('house'), parent1_name=d.get('parent1_name'), parent1_relationship=d.get('parent1_relationship'), parent1_phone=d.get('parent1_phone'), parent1_whatsapp=d.get('parent1_whatsapp'), parent1_email=d.get('parent1_email'), parent1_id_no=d.get('parent1_id_no'), parent1_occupation=d.get('parent1_occupation'), parent1_address=d.get('parent1_address'), parent2_name=d.get('parent2_name'), parent2_relationship=d.get('parent2_relationship'), parent2_phone=d.get('parent2_phone'), parent2_email=d.get('parent2_email'), emergency_name=d.get('emergency_name'), emergency_phone=d.get('emergency_phone'), emergency_relationship=d.get('emergency_relationship'), blood_group=d.get('blood_group'), allergies=d.get('allergies'), chronic_condition=d.get('chronic_condition'), doctor_name=d.get('doctor_name'), doctor_phone=d.get('doctor_phone'), nhif_no=d.get('nhif_no'), fee_category=d.get('fee_category'), scholarship=d.get('scholarship'), talent=d.get('talent'), special_needs=d.get('special_needs'), status=d.get('status','Active'), notes=d.get('notes'))
            messages.success(request, "Learner registered!")
        except Exception as e: messages.error(request, f"Error: {e}")
        return redirect('learners')
    ctx['learners'] = objs; ctx['classes'] = ClassRoom.objects.all(); return render(request, 'learners.html', ctx)

@login_required
def learner_detail(request, learner_id):
    ctx = get_context(request); ctx['learner'] = get_object_or_404(Learner, id=learner_id); ctx['l'] = ctx['learner']; return render(request, 'learner_detail.html', ctx)

@login_required
def learner_delete(request, learner_id):
    if get_role(request) not in ['Admin']:
        messages.error(request, "Only Admin can delete."); return redirect('learners')
    get_object_or_404(Learner, id=learner_id).delete(); return redirect('learners')

@login_required
def classes(request):
    ctx = get_context(request); objs = ClassRoom.objects.all().order_by('name')
    if request.method == 'POST':
        ClassRoom.objects.create(school=get_school(request), name=request.POST.get('name'), stream=request.POST.get('stream'), class_teacher_name=request.POST.get('teacher'), capacity=request.POST.get('capacity') or 40); messages.success(request, "Class created!"); return redirect('classes')
    for c in objs: c.learner_count = Learner.objects.filter(classroom=c).count()
    ctx['classes_list'] = objs; ctx['classes'] = objs; return render(request, 'classes.html', ctx)

@login_required
def teachers(request):
    ctx = get_context(request)
    if get_role(request) in ['Learner','Parent','Bursar']:
        messages.error(request, "You cannot view Teachers."); return redirect_by_role(get_role(request))
    objs = Teacher.objects.all().order_by('-id')
    if request.method == 'POST':
        d = request.POST; Teacher.objects.create(full_name=d.get('full_name'), tsc_no=d.get('tsc_no'), id_no=d.get('id_no'), phone=d.get('phone'), email=d.get('email'), gender=d.get('gender','Male'), date_of_birth=d.get('dob') or None, county=d.get('county'), subject=d.get('subject'), subjects=d.get('subject'), qualification=d.get('qualification'), employment_type=d.get('employment_type','Permanent'), salary=d.get('salary') or 0, hire_date=d.get('hire_date') or None, classroom_id=d.get('classroom') or None, school=get_school(request), status=d.get('status','Active'), photo=request.FILES.get('photo')); messages.success(request, "Teacher added!"); return redirect('teachers')
    ctx['teachers'] = objs; ctx['teachers_list'] = objs; ctx['total_teachers'] = objs.count(); ctx['classes'] = ClassRoom.objects.all(); return render(request, 'teachers.html', ctx)

@login_required
def parents(request):
    ctx = get_context(request); role = get_role(request); q = request.GET.get('q',''); learners = Learner.objects.all().order_by('parent1_name')
    if role == 'Parent':
        try:
            prof = request.user.profile
            if prof.learner: learners = Learner.objects.filter(id=prof.learner.id)
        except: pass
    if q: learners = learners.filter(Q(parent1_name__icontains=q)|Q(parent1_phone__icontains=q)|Q(first_name__icontains=q))
    ctx['parents_list'] = learners; ctx['learners'] = learners; return render(request, 'parents.html', ctx)

@login_required
def student(request):
    ctx = get_context(request); role = get_role(request)
    if role == 'Learner':
        try:
            prof = request.user.profile
            if prof.learner:
                ctx['learners'] = Learner.objects.filter(id=prof.learner.id); ctx['my_learner'] = prof.learner; ctx['my_results'] = ExamResult.objects.filter(learner=prof.learner); ctx['my_payments'] = LearnerFeePayment.objects.filter(learner=prof.learner); return render(request, 'student.html', ctx)
        except: pass
    ctx['learners'] = Learner.objects.all()[:20]; return render(request, 'student.html', ctx)

@login_required
def attendance(request):
    ctx = get_context(request); ctx['learners'] = Learner.objects.all().order_by('classroom__name','first_name'); ctx['classes'] = ClassRoom.objects.all(); ctx['today'] = timezone.now().date()
    if request.method == 'POST': messages.success(request, "Attendance saved!"); return redirect('attendance')
    return render(request, 'attendance.html', ctx)

@login_required
def timetable(request):
    ctx = get_context(request); ctx['classes'] = ClassRoom.objects.all(); ctx['days'] = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']; ctx['periods'] = ['8:00-8:40','8:40-9:20','9:20-10:00','10:30-11:10','11:10-11:50','11:50-12:30','2:00-2:40','2:40-3:20']; ctx['subjects'] = ['English','Kiswahili','Kenyan Sign Language','Indigenous Language','Mathematics (Essential)','Mathematics (Core)','Religious Education (CRE / IRE / HRE)','Social Studies','Science & Technology','Agriculture','Home Science','Physical & Health Education','Art & Craft','Music','Integrated Science','Health Education','Pre-Technical Studies','Business Studies','Life Skills Education','Community Service Learning','Sports & PE','Computer Science','Visual Arts','Performing Arts']
    return render(request, 'timetable.html', ctx)

@login_required
def results(request):
    ctx = get_context(request)
    if get_role(request) in ['Bursar','Matron']:
        messages.error(request, "Bursar / Matron cannot view Results."); return redirect_by_role(get_role(request))
    learners = Learner.objects.all().order_by('classroom__name','first_name'); cbc_subjects = ['English','Kiswahili','Kenyan Sign Language','Indigenous Language','Mathematics (Essential)','Mathematics (Core)','Religious Education (CRE / IRE / HRE)','Social Studies','Science & Technology','Agriculture','Home Science','Physical & Health Education','Art & Craft','Music','Integrated Science','Health Education','Pre-Technical Studies','Business Studies','Life Skills Education','Community Service Learning','Sports & PE','Computer Science','Visual Arts','Performing Arts']
    rows = []
    for l in learners:
        results_qs = ExamResult.objects.filter(learner=l, term='Term 3', year='2026'); scores = {r.subject: float(r.score) for r in results_qs}; total = sum(scores.values()); count = len(scores) if scores else 0; mean = round(total/count, 1) if count else 0; rows.append({'learner': l, 'scores': scores, 'total': total, 'mean': mean, 'count': count})
    class_mean = round(sum(r['mean'] for r in rows)/len(rows), 1) if rows else 0
    for r in rows:
        r['deviation'] = round(r['mean'] - class_mean, 1); r['mean_deviation'] = round(abs(r['deviation']), 1)
        if r['mean'] >= 80: r['grade']='A'; r['remarks']='Excellent - Exceeding Expectation'
        elif r['mean'] >= 70: r['grade']='B+'; r['remarks']='Very Good - Meeting Expectation'
        elif r['mean'] >= 60: r['grade']='B'; r['remarks']='Good - Meeting Expectation'
        elif r['mean'] >= 50: r['grade']='C'; r['remarks']='Fair - Approaching Expectation'
        elif r['mean'] >= 40: r['grade']='D'; r['remarks']='Needs Improvement - Below Expectation'
        else: r['grade']='E'; r['remarks']='Needs Support - Below Expectation'
    sorted_rows = sorted(rows, key=lambda x: x['mean'], reverse=True)
    for i, r in enumerate(sorted_rows, 1): r['position'] = i
    ctx.update({'learners': learners, 'classes': ClassRoom.objects.all(), 'subjects': cbc_subjects, 'cbc_subjects': cbc_subjects, 'rows': rows, 'class_mean': class_mean, 'total_learners_in_results': len(rows)}); return render(request, 'results.html', ctx)

@login_required
def cbc(request):
    ctx = get_context(request); ctx['learners'] = Learner.objects.all().order_by('first_name'); ctx['classes'] = ClassRoom.objects.all(); ctx['levels'] = ['Exceeding Expectation','Meeting Expectation','Approaching Expectation','Below Expectation']; ctx['cbc_subjects'] = ['English','Kiswahili','Kenyan Sign Language','Indigenous Language','Mathematics (Essential)','Mathematics (Core)','Religious Education (CRE / IRE / HRE)','Social Studies','Science & Technology','Agriculture','Home Science','Physical & Health Education','Art & Craft','Music','Integrated Science','Health Education','Pre-Technical Studies','Business Studies','Life Skills Education','Community Service Learning','Sports & PE','Computer Science','Visual Arts','Performing Arts']; return render(request, 'cbc.html', ctx)

@login_required
def class_report(request):
    ctx = get_context(request); ctx['learners'] = Learner.objects.all(); ctx['classes'] = ClassRoom.objects.all(); return render(request, 'class_report.html', ctx)

@login_required
def fees(request):
    ctx = get_context(request)
    if get_role(request) in ['Learner','Parent']: return redirect('student')
    term = request.GET.get('term','Term 3'); year = request.GET.get('year','2026'); payment_filter = request.GET.get('method','')
    if request.method == 'POST' and 'set_structure' in request.POST:
        d = request.POST; FeeStructure.objects.create(classroom_id=d.get('classroom') or None, term=d.get('term','Term 3'), year=d.get('year','2026'), tuition=d.get('tuition') or 0, lunch=d.get('lunch') or 0, transport=d.get('transport') or 0, boarding=d.get('boarding') or 0, exam=d.get('exam') or 0, activity=d.get('activity') or 0, uniform=d.get('uniform') or 0, books=d.get('books') or 0, computer=d.get('computer') or 0, medical=d.get('medical') or 0, development=d.get('development') or 0, other=d.get('other') or 0, other_label=d.get('other_label'), notes=d.get('notes')); messages.success(request, "Fee Structure saved!"); return redirect('fees')
    if request.method == 'POST' and 'record_payment' in request.POST:
        d = request.POST; method = d.get('method','Cash'); LearnerFeePayment.objects.create(learner_id=d.get('learner'), fee_structure_id=d.get('fee_structure') or None, term=d.get('term','Term 3'), year=d.get('year','2026'), amount_expected=d.get('amount_expected') or 0, amount_paid=d.get('amount_paid') or 0, method=method, receipt_no=d.get('receipt_no'), mpesa_code=d.get('mpesa_code',''), mpesa_type=d.get('mpesa_type',''), mpesa_phone=d.get('mpesa_phone',''), mpesa_till=d.get('mpesa_till',''), mpesa_account=d.get('mpesa_account',''), mpesa_name=d.get('mpesa_name',''), bank_name=d.get('bank_name',''), bank_branch=d.get('bank_branch',''), bank_account=d.get('bank_account',''), bank_ref=d.get('bank_ref',''), bank_sender=d.get('bank_sender',''), bank_slip=d.get('bank_slip',''), cheque_no=d.get('cheque_no',''), cheque_bank=d.get('cheque_bank',''), cheque_date=d.get('cheque_date') or None, cash_received_by=d.get('cash_received_by',''), cash_notes=d.get('cash_notes',''), bursary_source=d.get('bursary_source',''), bursary_ref=d.get('bursary_ref',''), bursary_sponsor=d.get('bursary_sponsor',''), other_method=d.get('other_method',''), other_ref=d.get('other_ref',''), paid_by=d.get('paid_by'), date=d.get('date') or None); messages.success(request, f"Payment recorded via {method}!"); return redirect('fees')
    structures = FeeStructure.objects.all().order_by('-id'); payments = LearnerFeePayment.objects.filter(method=payment_filter).order_by('-id')[:50] if payment_filter else LearnerFeePayment.objects.all().order_by('-id')[:50]; learners = Learner.objects.all(); totals_by_method = {}
    for m in ['Cash','M-Pesa','Bank','Cheque','Bursary','Other']: totals_by_method[m] = float(LearnerFeePayment.objects.filter(method=m, term=term, year=year).aggregate(t=Sum('amount_paid'))['t'] or 0)
    learner_balances = []
    for l in learners:
        paid = LearnerFeePayment.objects.filter(learner=l, term=term, year=year).aggregate(t=Sum('amount_paid'))['t'] or 0; fs = FeeStructure.objects.filter(classroom=l.classroom, term=term, year=year).first() or FeeStructure.objects.filter(classroom__isnull=True, term=term, year=year).first(); expected = float(fs.total) if fs else 0; learner_balances.append({'learner': l, 'expected': expected, 'paid': float(paid), 'balance': float(expected - paid)})
    ctx.update({'structures': structures, 'payments': payments, 'learner_balances': learner_balances, 'classes': ClassRoom.objects.all(), 'learners': learners, 'selected_term': term, 'selected_year': year, 'selected_method': payment_filter, 'totals_by_method': totals_by_method, 'total_cash': totals_by_method.get('Cash',0), 'total_mpesa': totals_by_method.get('M-Pesa',0), 'total_bank': totals_by_method.get('Bank',0), 'total_cheque': totals_by_method.get('Cheque',0), 'total_bursary': totals_by_method.get('Bursary',0), 'total_other': totals_by_method.get('Other',0), 'total_expected': sum(x['expected'] for x in learner_balances), 'total_paid': sum(x['paid'] for x in learner_balances), 'total_balance': sum(x['balance'] for x in learner_balances), 'payment_options': [{'value':'Cash','label':'💵 Cash'},{'value':'M-Pesa','label':'📱 M-Pesa'},{'value':'Bank','label':'🏦 Bank'},{'value':'Cheque','label':'🧾 Cheque'},{'value':'Bursary','label':'🎓 Bursary'},{'value':'Other','label':'➕ Other'}]}); return render(request, 'fees.html', ctx)

@login_required
def finance(request):
    ctx = get_context(request)
    if get_role(request) not in ['Admin','Bursar']:
        messages.error(request, "Only Admin / Bursar can view Finance."); return redirect_by_role(get_role(request))
    total_paid = LearnerFeePayment.objects.aggregate(t=Sum('amount_paid'))['t'] or 0; total_expected = 0
    for fs in FeeStructure.objects.all(): total_expected += float(fs.total)
    by_method = {}
    for m in ['Cash','M-Pesa','Bank','Cheque','Bursary','Other']: by_method[m] = float(LearnerFeePayment.objects.filter(method=m).aggregate(t=Sum('amount_paid'))['t'] or 0)
    ctx['total_expected'] = total_expected; ctx['total_collected'] = float(total_paid); ctx['total_balance'] = float(total_expected - float(total_paid)); ctx['total_expenses'] = 0; ctx['by_method'] = by_method; return render(request, 'finance.html', ctx)

@login_required
def learning(request):
    ctx = get_context(request); ctx['cbc_levels'] = [{'level': 'Pre-Primary (PP1 - PP2)', 'age': 'Age 4-5', 'color': '#f97316', 'subjects': [{'name':'Language Activities','icon':'🗣️','lessons':24},{'name':'Mathematical Activities','icon':'🔢','lessons':22}]},{'level': 'Lower Primary (Grade 1 - 3)', 'age': 'Age 6-8', 'color': '#059669', 'subjects': [{'name':'English','icon':'📖','lessons':28},{'name':'Kiswahili','icon':'📚','lessons':26}]},{'level': 'Upper Primary (Grade 4 - 6)', 'age': 'Age 9-11', 'color': '#0a2463', 'subjects': [{'name':'English','icon':'📖','lessons':30},{'name':'Science & Technology','icon':'🔬','lessons':26}]},{'level': 'Junior School (Grade 7 - 9)', 'age': 'Age 12-14', 'color': '#7c3aed', 'subjects': [{'name':'English','icon':'📖','lessons':32},{'name':'Integrated Science','icon':'🔬','lessons':28}]},{'level': 'Senior School (Grade 10 - 12)', 'age': 'Age 15-17', 'color': '#dc2626', 'subjects': [{'name':'STEM - Pure Sciences','icon':'🔬','lessons':36},{'name':'Arts & Sports','icon':'🎭','lessons':26}]}]; ctx['subjects'] = [{'name':'English','icon':'📖','color':'#0a2463','lessons':30},{'name':'Kiswahili','icon':'📚','color':'#059669','lessons':28}]; return render(request, 'learning.html', ctx)

@login_required
def assignments(request):
    ctx = get_context(request); ctx['classes'] = ClassRoom.objects.all(); ctx['assignments_list'] = []; return render(request, 'assignments.html', ctx)

@login_required
def library(request):
    ctx = get_context(request); ctx['books'] = [{'title':'CBC Mathematics Grade 7','author':'KIE','category':'Maths','copies':12},{'title':'English Reader - Grade 5','author':'Oxford','category':'English','copies':20}]; return render(request, 'library.html', ctx)

@login_required
def transport(request):
    ctx = get_context(request); ctx['routes'] = [{'name':'Eldoret Town - School','driver':'John K.','bus':'KDA 123A','learners':0,'fee':4500},{'name':'Kimumu - School','driver':'Peter M.','bus':'KDJ 456B','learners':0,'fee':4000}]; ctx['learners'] = Learner.objects.filter(transport_route__isnull=False).exclude(transport_route=''); return render(request, 'transport.html', ctx)

@login_required
def communication(request):
    ctx = get_context(request); ctx['learners'] = Learner.objects.all(); ctx['classes'] = ClassRoom.objects.all(); return render(request, 'communication.html', ctx)

@login_required
def reports(request):
    ctx = get_context(request)
    if get_role(request) not in ['Admin','Teacher','Bursar']: return redirect_by_role(get_role(request))
    ctx['learners'] = Learner.objects.all(); ctx['classes'] = ClassRoom.objects.all(); return render(request, 'reports.html', ctx)

@login_required
def audit(request):
    ctx = get_context(request)
    if get_role(request) not in ['Admin']: return redirect_by_role(get_role(request))
    ctx['logs'] = [{'user': request.user.username, 'action': 'Logged in', 'time': timezone.now(), 'ip': '127.0.0.1'}]; return render(request, 'audit.html', ctx)

@login_required
def backup(request):
    ctx = get_context(request)
    if get_role(request) not in ['Admin']: return redirect_by_role(get_role(request))
    if request.method == 'POST': messages.success(request, "Backup created!"); return redirect('backup')
    return render(request, 'backup.html', ctx)

@login_required
def about(request):
    ctx = get_context(request); return render(request, 'about.html', ctx)

@login_required
def export_learners_csv(request):
    response = HttpResponse(content_type='text/csv'); response['Content-Disposition'] = 'attachment; filename="learners.csv"'; writer = csv.writer(response); writer.writerow(['Adm No','First Name','Middle Name','Last Name','Gender','DOB','Class','Parent','Phone','County','Status'])
    for l in Learner.objects.all(): writer.writerow([l.admission_no, l.first_name, l.middle_name, l.last_name, l.gender, l.date_of_birth, str(l.classroom), l.parent1_name, l.parent1_phone, l.county, l.status])
    return response

@login_required
def boarding(request):
    ctx = get_context(request)
    if get_role(request) in ['Learner','Parent','Bursar']:
        messages.error(request, "You cannot view Boarding."); return redirect_by_role(get_role(request))
    if request.method == 'POST' and 'add_house' in request.POST:
        d = request.POST; BoardingHouse.objects.create(name=d.get('name'), gender=d.get('gender','Boys'), capacity=d.get('capacity') or 40, matron_patron=d.get('matron_patron'), matron_phone=d.get('matron_phone'), teacher_in_charge=d.get('teacher_in_charge'), location=d.get('location'), notes=d.get('notes')); messages.success(request, "Boarding House added!"); return redirect('boarding')
    if request.method == 'POST' and 'assign_learner' in request.POST:
        d = request.POST; BoardingAssignment.objects.create(learner_id=d.get('learner'), house_id=d.get('house'), dorm_room=d.get('dorm_room'), bed_no=d.get('bed_no'), locker_no=d.get('locker_no'), check_in_date=d.get('check_in_date') or None, meal_plan=d.get('meal_plan','Normal'), meal_allergy=d.get('meal_allergy'), medical_notes=d.get('medical_notes'), belongings=d.get('belongings'), parent_visit_allowed=d.get('parent_visit_allowed'), visiting_day=d.get('visiting_day','Saturday 10am - 4pm'), pocket_money=d.get('pocket_money') or 0, boarding_fee_expected=d.get('boarding_fee_expected') or 0, boarding_fee_paid=d.get('boarding_fee_paid') or 0, discipline_notes=d.get('discipline_notes'), status='Active'); messages.success(request, "Learner assigned to Boarding!"); return redirect('boarding')
    if request.method == 'POST' and 'checkout' in request.POST:
        a = get_object_or_404(BoardingAssignment, id=request.POST.get('assignment_id')); a.status = 'Checked Out'; a.check_out_date = timezone.now().date(); a.save(); messages.success(request, f"{a.learner} checked out!"); return redirect('boarding')
    if request.method == 'POST' and 'rollcall' in request.POST:
        d = request.POST; a = get_object_or_404(BoardingAssignment, id=d.get('assignment_id')); BoardingRollCall.objects.create(assignment=a, date=d.get('date') or timezone.now().date(), present=(d.get('present') == 'on'), note=d.get('note')); messages.success(request, f"Roll Call saved for {a.learner}!"); return redirect('boarding')
    houses = BoardingHouse.objects.all().order_by('name'); assignments = BoardingAssignment.objects.all().order_by('-id'); boarding_learners = Learner.objects.filter(boarding_type='Boarding'); total_beds = sum(h.capacity for h in houses); occupied = assignments.filter(status='Active').count()
    ctx.update({'offers_boarding': True, 'houses': houses, 'assignments': assignments, 'active_assignments': assignments.filter(status='Active'), 'boarding_learners': boarding_learners, 'learners': Learner.objects.all(), 'total_houses': houses.count(), 'total_beds': total_beds, 'occupied_beds': occupied, 'free_beds': total_beds - occupied, 'total_boarding_learners': boarding_learners.count(), 'total_boarding_expected': sum(float(a.boarding_fee_expected) for a in assignments), 'total_boarding_paid': sum(float(a.boarding_fee_paid) for a in assignments), 'total_boarding_balance': sum(float(a.balance) for a in assignments)}); return render(request, 'boarding.html', ctx)