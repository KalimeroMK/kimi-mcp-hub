---
name: laravel-engineer
description: Laravel, PHP, Eloquent, Blade, Livewire, and Queues specialist.
type: prompt
whenToUse: When the user mentions Laravel, Eloquent, Blade, PHP, Livewire, or Artisan.
disableModelInvocation: false
---
# 🎨 Laravel Engineer

When activated, delegate to **coder** sub-agent with Laravel constraints.

## Principles

### Eloquent First
```php
// ✅ Eloquent relationships
class User extends Model
{
    public function posts(): HasMany
    {
        return $this->hasMany(Post::class);
    }

    public function roles(): BelongsToMany
    {
        return $this->belongsToMany(Role::class);
    }
}

// ✅ Eager loading (N+1 prevention)
$users = User::with(['posts', 'roles'])->get();

// ✅ Query scopes
class Post extends Model
{
    public function scopePublished($query)
    {
        return $query->where('status', 'published');
    }
}

$posts = Post::published()->latest()->get();
```

### Service Container
```php
// ✅ Bind in AppServiceProvider
$this->app->bind(PaymentInterface::class, StripePayment::class);

// ✅ Resolve via constructor injection
class OrderController extends Controller
{
    public function __construct(
        private PaymentInterface $payment
    ) {}
}

// ✅ Facades for convenience (sparingly)
Cache::remember('users', 3600, fn() => User::all());
```

### Form Requests
```php
// ✅ Validation in dedicated class
class StoreUserRequest extends FormRequest
{
    public function authorize(): bool
    {
        return $this->user()->can('create-users');
    }

    public function rules(): array
    {
        return [
            'name' => ['required', 'string', 'max:255'],
            'email' => ['required', 'email', 'unique:users'],
            'password' => ['required', 'min:8', 'confirmed'],
        ];
    }
}

// ✅ Use in controller
class UserController extends Controller
{
    public function store(StoreUserRequest $request): JsonResponse
    {
        $user = User::create($request->validated());
        return response()->json($user, 201);
    }
}
```

### API Resources
```php
// ✅ Transform data consistently
class UserResource extends JsonResource
{
    public function toArray($request): array
    {
        return [
            'id' => $this->id,
            'name' => $this->name,
            'email' => $this->email,
            'posts' => PostResource::collection($this->whenLoaded('posts')),
            'created_at' => $this->created_at->toIso8601String(),
        ];
    }
}
```

## Blade & Components

### Components
```php
// app/View/Components/Alert.php
class Alert extends Component
{
    public function __construct(
        public string $type = 'info',
        public string $message = ''
    ) {}

    public function render(): View
    {
        return view('components.alert');
    }
}

// resources/views/components/alert.blade.php
<div class="alert alert-{{ $type }}">
    {{ $message }}
</div>

// Usage
<x-alert type="danger" message="Something went wrong!" />
```

### Layouts
```php
// resources/views/layouts/app.blade.php
<!DOCTYPE html>
<html>
<head>
    <title>@yield('title', 'My App')</title>
    @vite(['resources/css/app.css', 'resources/js/app.js'])
</head>
<body>
    @include('partials.nav')
    <main>
        @yield('content')
    </main>
</body>
</html>

// resources/views/dashboard.blade.php
@extends('layouts.app')
@section('title', 'Dashboard')
@section('content')
    <h1>Welcome, {{ auth()->user()->name }}</h1>
@endsection
```

## Livewire

```php
// app/Livewire/Counter.php
class Counter extends Component
{
    public int $count = 0;

    public function increment(): void
    {
        $this->count++;
    }

    public function render(): View
    {
        return view('livewire.counter');
    }
}

// resources/views/livewire/counter.blade.php
<div>
    <button wire:click="increment">+</button>
    <span>{{ $count }}</span>
</div>
```

## Queues & Jobs

```php
// app/Jobs/SendWelcomeEmail.php
class SendWelcomeEmail implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public function __construct(public User $user) {}

    public function handle(): void
    {
        Mail::to($this->user)->send(new WelcomeMail($this->user));
    }
}

// Dispatch
SendWelcomeEmail::dispatch($user);
SendWelcomeEmail::dispatch($user)->delay(now()->addMinutes(10));
SendWelcomeEmail::dispatch($user)->onQueue('emails');
```

## Testing

### Pest / PHPUnit
```php
// Feature test
it('can create a user', function () {
    $response = $this->postJson('/api/users', [
        'name' => 'John Doe',
        'email' => 'john@example.com',
        'password' => 'password123',
        'password_confirmation' => 'password123',
    ]);

    $response->assertCreated()
        ->assertJsonPath('name', 'John Doe');

    expect(User::where('email', 'john@example.com')->exists())->toBeTrue();
});

// Unit test
it('formats price correctly', function () {
    $product = Product::factory()->make(['price' => 1999]);
    expect($product->formatted_price)->toBe('$19.99');
});
```

### Factories
```php
class UserFactory extends Factory
{
    public function definition(): array
    {
        return [
            'name' => fake()->name(),
            'email' => fake()->unique()->safeEmail(),
            'email_verified_at' => now(),
            'password' => Hash::make('password'),
        ];
    }

    public function admin(): static
    {
        return $this->state(fn(array $attributes) => [
            'role' => 'admin',
        ]);
    }
}
```

## Plugin Discovery (Packagist)

```bash
# Search for packages
composer search laravel permission

# Install
composer require spatie/laravel-permission

# Publish config
php artisan vendor:publish --provider="Spatie\Permission\PermissionServiceProvider"

# Run migrations
php artisan migrate
```

### Popular Laravel Packages
| Package | Purpose |
|---------|---------|
| spatie/laravel-permission | RBAC authorization |
| spatie/laravel-medialibrary | File uploads |
| spatie/laravel-query-builder | API filtering/sorting |
| laravel/sanctum | API authentication |
| laravel/socialite | OAuth login |
| inertiajs/inertia-laravel | SPA without API |
| livewire/livewire | Dynamic components |
| filament/filament | Admin panels |
| laravel/nova | Admin dashboard |
| barryvdh/laravel-debugbar | Local debugging |

## Security

### CSRF Protection
```php
// ✅ Automatic in forms
<form method="POST" action="/profile">
    @csrf
    <!-- fields -->
</form>

// ✅ API routes exempt
Route::middleware('auth:sanctum')->group(function () {
    // CSRF not needed for stateless API
});
```

### SQL Injection Prevention
```php
// ✅ Eloquent prevents injection automatically
User::where('email', $request->email)->first();

// ✅ Parameterized queries for raw
DB::select('SELECT * FROM users WHERE id = ?', [$id]);

// ❌ Never do this
DB::select("SELECT * FROM users WHERE id = $id");
```

### XSS Prevention
```php
// ✅ Blade auto-escapes output
{{ $user->name }}

// ✅ Raw output only when safe
{!! $user->bio !!}  // Must be sanitized first
```

## Deployment

### Forge (managed servers)
```bash
# Connect repo, auto-deploy on push
# SSL, queues, cron, all configured
```

### Vapor (serverless)
```bash
# Deploy to AWS Lambda
vapor deploy production
```

### Docker
```dockerfile
FROM php:8.3-fpm
RUN apt-get update && apt-get install -y libpq-dev
RUN docker-php-ext-install pdo pdo_pgsql
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer
WORKDIR /var/www
COPY . .
RUN composer install --no-dev --optimize-autoloader
RUN php artisan optimize
```

## Tooling
- **Sail** — Docker development environment
- **Pint** — Code style fixer (Laravel's Prettier)
- **Telescope** — Local debugging dashboard
- **Horizon** — Queue monitoring dashboard
- **Scout** — Full-text search (Algolia, Meilisearch)
- **Socialite** — OAuth authentication
- **Cashier** — Stripe/Paddle billing
