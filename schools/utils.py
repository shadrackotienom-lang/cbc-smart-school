from .models import School
def global_context(request):
    schools = School.objects.filter(is_active=True)
    current = None
    if request.user.is_authenticated:
        sid = request.session.get('school_id')
        if sid:
            try: current = School.objects.get(id=sid)
            except: pass
        if not current and schools.exists(): current = schools.first()
    return {'schools': schools, 'school': current, 'current_school': current}
def get_current_school(request):
    sid = request.session.get('school_id')
    if sid:
        try: return School.objects.get(id=sid)
        except: pass
    return School.objects.filter(is_active=True).first()
def log_action(request, action, details=''):
    try:
        from .models import AuditLog
        AuditLog.objects.create(user=request.user if request.user.is_authenticated else None, school=get_current_school(request), action=action, details=details, ip_address=request.META.get('REMOTE_ADDR'))
    except: pass
def fee_balance(learner, term='Term 1'):
    from .models import FeeStructure
    s = FeeStructure.objects.filter(school=learner.school, grade=learner.grade, term=term).first()
    exp = float(s.total()) if s else 0
    paid = sum(float(p.amount) for p in learner.payment_set.filter(term=term))
    return exp - paid