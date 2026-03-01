variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = ""
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = ""
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  default     = ""
}

variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
  default     = ""
}

variable "openai_api_key" {
  description = "OpenAI API key for the application"
  type        = string
  sensitive   = true
  default     = ""
}

variable "docker_image_tag" {
  description = "Tag for the Docker image"
  type        = string
  default     = "latest"
}

variable "db_port" {
  description = "Database port"
  type        = string
  default     = "5432"
}

variable "db_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
  default     = ""
}

variable "django_secret_key" {
  description = "Django secret key for production"
  type        = string
  sensitive   = true
  default     = ""
}

variable "django_superuser_username" {
  description = "Django superuser username"
  type        = string
  default     = ""
}

variable "django_superuser_password" {
  description = "Django superuser password"
  type        = string
  sensitive   = true
  default     = ""
}

variable "django_superuser_email" {
  description = "Django superuser email"
  type        = string
  default     = ""
}

variable "num_interviews" {
  description = "Number of interview simulations"
  type        = string
  default     = "100"
}

variable "openai_chat_model" {
  description = "OpenAI model for chat"
  type        = string
  default     = ""
}

variable "openai_analysis_model" {
  description = "OpenAI model for analysis"
  type        = string
  default     = ""
}

variable "openai_embedding_model" {
  description = "OpenAI embedding model"
  type        = string
  default     = ""
}

variable "num_concurrent_interviews" {
  description = "Number of concurrent interview simulations"
  type        = string
  default     = "10"
}

variable "postgres_db" {
  description = "PostgreSQL database name"
  type        = string
  default     = "interviews_db"
}