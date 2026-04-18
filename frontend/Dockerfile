# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy the rest of the application
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM node:20-alpine AS runner

WORKDIR /app

# Set environment to production
ENV NODE_ENV=production

# Install PM2 globally
RUN npm install -g pm2

# Copy necessary files from builder
COPY --from=builder /app/next.config.ts ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Create PM2 ecosystem file
RUN echo 'module.exports = { apps: [{ name: "frontend", script: "server.js", instances: "max", exec_mode: "cluster", env: { NODE_ENV: "production" } }] }' > ecosystem.config.js

# Expose the port the app runs on
EXPOSE 3000

# Set the command to run the app with PM2
CMD ["pm2-runtime", "ecosystem.config.js"]
