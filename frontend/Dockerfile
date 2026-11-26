FROM nginx:alpine
RUN apk add --no-cache openssl
COPY index.html how-it-works.html /usr/share/nginx/html/
COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY 25-auth.sh /docker-entrypoint.d/25-auth.sh
RUN chmod +x /docker-entrypoint.d/25-auth.sh
