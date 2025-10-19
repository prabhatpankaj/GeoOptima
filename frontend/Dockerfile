# -------------------------------
# Stage 1: Base environment
# -------------------------------
FROM node:20-alpine AS base
WORKDIR /app

# Copy dependencies first for caching
COPY package*.json ./
RUN npm install --legacy-peer-deps

# Copy app source
COPY . .

# Expose the Next.js dev server
EXPOSE 3000

# Default command for local dev
CMD ["npm", "run", "dev"]
