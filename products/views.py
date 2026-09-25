from django.shortcuts import render

def scan(request):
    return render(request, "products/scan.html")
