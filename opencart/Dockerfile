FROM php:8.2-apache

RUN apt-get update \
 && apt-get install -y --no-install-recommends libpng-dev libjpeg-dev libfreetype6-dev libzip-dev libcurl4-openssl-dev unzip curl \
 && docker-php-ext-configure gd --with-freetype --with-jpeg \
 && docker-php-ext-install -j2 gd mysqli zip \
 && a2enmod rewrite headers \
 && rm -rf /var/lib/apt/lists/*

ARG OC_VERSION=4.1.0.4
RUN curl -fsSL -o /tmp/oc.zip "https://github.com/opencart/opencart/releases/download/${OC_VERSION}/opencart-${OC_VERSION}.zip" \
 && unzip -q /tmp/oc.zip -d /tmp/oc \
 && cp -r /tmp/oc/upload/. /var/www/html/ \
 && rm -rf /tmp/oc /tmp/oc.zip \
 && cp /var/www/html/config-dist.php /var/www/html/config.php \
 && cp /var/www/html/admin/config-dist.php /var/www/html/admin/config.php \
 && cp /var/www/html/.htaccess.txt /var/www/html/.htaccess \
 && chown -R www-data:www-data /var/www/html

RUN sed -i 's#AllowOverride None#AllowOverride All#' /etc/apache2/apache2.conf

# The lab's robots.txt and the sitemap rewrite, placed before OpenCart's catch-all rule
COPY robots.txt /var/www/html/robots.txt
COPY htaccess.extra /tmp/htaccess.extra
RUN sed -i '/^RewriteBase/r /tmp/htaccess.extra' /var/www/html/.htaccess && rm /tmp/htaccess.extra
