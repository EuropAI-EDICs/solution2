# Static EDIC Marketplace for Fly.io
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY .htpasswd /etc/nginx/.htpasswd
COPY index.html styles.css app.js i18n.js recipes-i18n.js process-kinds.js /usr/share/nginx/html/
COPY data/ /usr/share/nginx/html/data/

EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
