from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from .models import Product, Category, CartItem, ScrollingText, Review, HomePoster
from .forms import ContactForm
from django.core.mail import send_mail
from django.conf import settings

def home(request):
    categories = Category.objects.all()
    products = Product.objects.all()[:8]  # Show only 8 products on home
    reviews = Review.objects.all().order_by('-created_at')[:5]
    posters = HomePoster.objects.filter(is_active=True)
    return render(request, 'store/home.html', {
        'categories': categories,
        'products': products,
        'reviews': reviews,
        'posters': posters
    })

@login_required
def view_cart(request):
    cart_items = CartItem.objects.filter(user=request.user)
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render(request, 'store/cart.html', {
        'cart_items': cart_items,
        'total': total
    })

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.GET.get('quantity', 1))
    
    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        product=product,
        defaults={'quantity': quantity}
    )
    
    if not created:
        cart_item.quantity += quantity
        cart_item.save()
    
    return redirect('cart')

@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)
    cart_item.delete()
    return redirect('cart')

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    
    # Remove password help text
    form.fields['password1'].help_text = None
    form.fields['password2'].help_text = None
    
    return render(request, 'store/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'store/login.html', {'form': form})

@login_required
def profile(request):
    # Get user's order history (cart items that have been purchased)
    order_history = CartItem.objects.filter(user=request.user).order_by('-added_at')
    return render(request, 'store/profile.html', {
        'order_history': order_history
    })

# Add new view for contact page
def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Send email
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            phone = form.cleaned_data['phone']
            comment = form.cleaned_data['comment']
            
            message = f"Name: {name}\nEmail: {email}\nPhone: {phone}\n\nMessage:\n{comment}"
            
            send_mail(
                'New Contact Form Submission - SWANANDI AGRO',
                message,
                settings.DEFAULT_FROM_EMAIL,
                ['ykdere63@gmail.com'],
                fail_silently=False,
            )
            
            return render(request, 'store/contact_success.html')
    else:
        form = ContactForm()
    
    return render(request, 'store/contact.html', {'form': form})

def category_products(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    products = Product.objects.filter(category=category)
    return render(request, 'store/category_products.html', {
        'category': category,
        'products': products
    })