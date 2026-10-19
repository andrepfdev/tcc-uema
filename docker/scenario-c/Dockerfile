FROM dunglas/frankenphp:1.13.0-php8.3.35@sha256:3a1dfb9404aceb016493f6c18989cc2b66ce62c6de2a79ae6e3b3dfe7f94094a

# git necessário para o Composer em imagens Debian
RUN apt-get update && apt-get install -y --no-install-recommends git unzip && rm -rf /var/lib/apt/lists/*

# Extensões para CI4
RUN install-php-extensions opcache intl pgsql pdo_pgsql

# OPcache — mesmo nível dos outros cenários
COPY docker/scenario-c/opcache.ini /usr/local/etc/php/conf.d/opcache.ini

# Instalar composer
COPY --from=composer:2@sha256:af98f42dfff7c68ba8d53c2164fd9fde1087b7d449514baa38c418b1f6bc4bac /usr/bin/composer /usr/bin/composer

WORKDIR /app

# Copiar código da aplicação CI4
# Inclui public/frankenphp-worker.php (suporte nativo CI4 >= 4.7.0)
COPY apps/ci4-base/ .

# Instalar dependências (CI4 >= 4.7 para suporte nativo ao Worker Mode)
RUN composer install --no-dev --optimize-autoloader --no-interaction --no-scripts

# Gera public/frankenphp-worker.php via comando oficial do CI4
RUN php spark worker:install --no-interaction

# Permissões de escrita para o CI4
RUN mkdir -p writable/{cache,logs,session,uploads,debugbar} \
    && chmod -R 777 writable/

# Caddyfile oficial gerado pelo `php spark worker:install`
# Worker mode com 4 workers (mesmo número de pm.max_children do Cenário A)
COPY docker/scenario-c/Caddyfile /etc/frankenphp/Caddyfile

ENV SCENARIO_NAME=scenario-c
ENV COMPUTE_SIZE=1000
ENV CI_ENVIRONMENT=production
ENV SERVER_NAME=":8080"

EXPOSE 8080
