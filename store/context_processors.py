from .models import ScrollingText

def scrolling_text(request):
    active_text = ScrollingText.objects.filter(is_active=True).first()
    return {'scrolling_text': active_text.text if active_text else None}