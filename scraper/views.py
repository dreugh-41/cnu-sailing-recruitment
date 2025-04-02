from django.shortcuts import render

# Create your views here.
def index(request):
    """
    Placeholder view for the scraper app.
    This app's functionality is currently integrated with the sailors app.
    """
    return render(request, 'scraper/index.html')