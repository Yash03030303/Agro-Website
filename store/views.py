from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from .models import Product, Category, CartItem, ScrollingText, Review, HomePoster, Order
from .forms import ContactForm
from .forms import CheckoutForm
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponse
import razorpay
from django.views.decorators.csrf import csrf_exempt

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

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))

@login_required
def checkout(request):
    cart_items = CartItem.objects.filter(user=request.user)
    if not cart_items:
        return redirect('cart')
    
    total = sum(item.product.price * item.quantity for item in cart_items)
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Create order
            order = Order.objects.create(
                user=request.user,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                phone=form.cleaned_data['phone'],
                address=form.cleaned_data['address'],
                city=form.cleaned_data['city'],
                state=form.cleaned_data['state'],
                pin_code=form.cleaned_data['pin_code'],
                total_amount=total
            )
            
            # Create Razorpay order
            currency = 'INR'
            amount = int(total * 100)  # Razorpay expects amount in paise
            
            razorpay_order = razorpay_client.order.create({
                'amount': amount,
                'currency': currency,
                'payment_capture': '1'  # Auto capture payment
            })
            
            # Save Razorpay order ID
            order.razorpay_order_id = razorpay_order['id']
            order.save()
            
            # Prepare context for payment
            context = {
                'razorpay_order_id': razorpay_order['id'],
                'razorpay_merchant_key': settings.RAZORPAY_API_KEY,
                'razorpay_amount': amount,
                'currency': currency,
                'callback_url': request.build_absolute_uri(reverse('payment_handler')),
                'order': order,
                'cart_items': cart_items,
                'total': total
            }
            
            return render(request, 'store/payment.html', context)
    else:
        form = CheckoutForm()
    
    return render(request, 'store/checkout.html', {
        'form': form,
        'cart_items': cart_items,
        'total': total
    })

@csrf_exempt
def payment_handler(request):
    if request.method == 'POST':
        try:
            # Get payment details from request
            payment_id = request.POST.get('razorpay_payment_id', '')
            razorpay_order_id = request.POST.get('razorpay_order_id', '')
            signature = request.POST.get('razorpay_signature', '')
            
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            
            # Verify the payment signature
            razorpay_client.utility.verify_payment_signature(params_dict)
            
            # Get order
            order = Order.objects.get(razorpay_order_id=razorpay_order_id)
            
            # Mark order as paid
            order.razorpay_payment_id = payment_id
            order.razorpay_signature = signature
            order.is_paid = True
            order.save()
            
            # Clear cart
            CartItem.objects.filter(user=request.user).delete()
            
            return redirect('order_success', order_id=order.id)
        except:
            # Signature verification failed
            return HttpResponse("Payment verification failed", status=400)
    else:
        return HttpResponse("Invalid request", status=400)

@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'store/order_success.html', {'order': order})

@login_required
def update_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
        else:
            cart_item.delete()
    return redirect('cart')

def user_logout(request):
    logout(request)
    return redirect('home')