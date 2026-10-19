FROM php:8.3.35-fpm-alpine@sha256:454b11c8907e32878ce92e87b13c14e1bbe6e1b10f4f96d4a19c9b62ec675d41

# icu-dev: necessário para ext-intl (requerida pelo CI4)
# libpq-dev: necessário para ext-pgsql/pdo_pgsql
RUN apk add --no-cache icu-dev libpq-dev git unzip \
    && docker-php-ext-install opcache intl pgsql pdo_pgsql

# OPcache para benchmark justo (Scenario A recebe todos os otimizadores que tem direito)
COPY docker/scenario-a/opcache.ini /usr/local/etc/php/conf.d/opcache.ini

# Instalar composer
COPY --from=composer:2@sha256:af98f42dfff7c68ba8d53c2164fd9fde1087b7d449514baa38c418b1f6bc4bac /usr/bin/composer /usr/bin/composer

WORKDIR /var/www/html

# Copiar código da aplicação
COPY apps/ci4-base/ .

# Instalar dependências
RUN composer install --no-dev --optimize-autoloader --no-interaction --no-scripts

# Permissões de escrita para o CI4
RUN mkdir -p writable/{cache,logs,session,uploads,debugbar} \
    && chmod -R 777 writable/

# Variáveis de ambiente sobrescritas pelo docker-compose
ENV SCENARIO_NAME=scenario-a
ENV COMPUTE_SIZE=1000
ENV CI_ENVIRONMENT=production

EXPOSE 9000
CMD ["php-fpm"]
