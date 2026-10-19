FROM dunglas/frankenphp:1.13.0-php8.3.35@sha256:3a1dfb9404aceb016493f6c18989cc2b66ce62c6de2a79ae6e3b3dfe7f94094a

# git necessário para o Composer em imagens Debian
RUN apt-get update && apt-get install -y --no-install-recommends git unzip && rm -rf /var/lib/apt/lists/*

# Extensões para Laravel
RUN install-php-extensions opcache pcntl pgsql pdo_pgsql

# OPcache — mesmo nível dos outros cenários
COPY docker/scenario-d/opcache.ini /usr/local/etc/php/conf.d/opcache.ini

# Instalar composer
COPY --from=composer:2@sha256:af98f42dfff7c68ba8d53c2164fd9fde1087b7d449514baa38c418b1f6bc4bac /usr/bin/composer /usr/bin/composer

WORKDIR /app

# Copiar app Laravel
COPY apps/laravel-octane/ .

# Instalar dependências
RUN composer install --no-dev --optimize-autoloader --no-interaction --no-scripts

# Otimizações de produção do Laravel
RUN php artisan config:cache \
    && php artisan route:cache \
    && php artisan event:cache

# Permissões de armazenamento
RUN chmod -R 777 storage bootstrap/cache

ENV SCENARIO_NAME=scenario-d
ENV COMPUTE_SIZE=1000
ENV APP_ENV=production
ENV APP_DEBUG=false
ENV OCTANE_SERVER=frankenphp
ENV SERVER_NAME=":8080"

EXPOSE 8080

# Octane com FrankenPHP — 4 workers para comparação justa com os outros cenários
CMD ["php", "artisan", "octane:frankenphp", "--workers=4", "--port=8080", "--host=0.0.0.0"]
