FROM dunglas/frankenphp:1.13.0-php8.3.35@sha256:3a1dfb9404aceb016493f6c18989cc2b66ce62c6de2a79ae6e3b3dfe7f94094a

# git necessário para o Composer em imagens Debian
RUN apt-get update && apt-get install -y --no-install-recommends git unzip && rm -rf /var/lib/apt/lists/*

# Extensões para CI4
RUN install-php-extensions opcache intl pgsql pdo_pgsql

# OPcache — mesmo nível de otimização do Cenário A para comparação justa
COPY docker/scenario-b/opcache.ini /usr/local/etc/php/conf.d/opcache.ini

# Instalar composer
COPY --from=composer:2@sha256:af98f42dfff7c68ba8d53c2164fd9fde1087b7d449514baa38c418b1f6bc4bac /usr/bin/composer /usr/bin/composer

WORKDIR /app

# Copiar código da aplicação CI4
COPY apps/ci4-base/ .

# Instalar dependências
RUN composer install --no-dev --optimize-autoloader --no-interaction --no-scripts

# Permissões de escrita para o CI4
RUN mkdir -p writable/{cache,logs,session,uploads,debugbar} \
    && chmod -R 777 writable/

# Caddyfile para modo Classic (sem diretiva worker — comportamento igual ao PHP-FPM)
COPY docker/scenario-b/Caddyfile /etc/frankenphp/Caddyfile

ENV SCENARIO_NAME=scenario-b
ENV COMPUTE_SIZE=1000
ENV CI_ENVIRONMENT=production
ENV SERVER_NAME=":8080"

EXPOSE 8080
