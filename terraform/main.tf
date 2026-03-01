terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

# Container registry
resource "azurerm_container_registry" "acr" {
  name                = replace(replace(var.project_name, "-", ""), "_", "") # only letters and numbers
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = true
}

# Automated build & push the docker image to ACR
resource "null_resource" "docker_build_push" {
  triggers = { always_run = timestamp() }

  provisioner "local-exec" {
    working_dir = "${path.module}/.."
    command     = <<-EOT
      az acr login --name ${azurerm_container_registry.acr.name}
      docker build --platform linux/amd64 -f docker/prod.dockerfile -t ${azurerm_container_registry.acr.login_server}/${var.project_name}:${var.docker_image_tag} .
      docker push ${azurerm_container_registry.acr.login_server}/${var.project_name}:${var.docker_image_tag}
    EOT
  }

  depends_on = [azurerm_container_registry.acr]
}

# PostgreSQL server
resource "azurerm_postgresql_flexible_server" "db" {
  name                          = "${var.project_name}-pgdb"
  resource_group_name           = var.resource_group_name
  location                      = var.location
  version                       = "16"
  administrator_login           = "pgadmin"
  administrator_password        = var.db_password
  storage_mb                    = 32768
  sku_name                      = "B_Standard_B1ms"
  zone                          = "1"
  public_network_access_enabled = true
}

# Postgres DB
resource "azurerm_postgresql_flexible_server_database" "app" {
  name      = var.postgres_db
  server_id = azurerm_postgresql_flexible_server.db.id
}

# Allowed services
resource "azurerm_postgresql_flexible_server_firewall_rule" "allowed_services" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.db.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# Logs
resource "azurerm_log_analytics_workspace" "logs" {
  name                = "${var.project_name}-logs"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

# Container env
resource "azurerm_container_app_environment" "env" {
  name                       = "${var.project_name}-env"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.logs.id
}

# Django app
resource "azurerm_container_app" "web" {
  name                         = var.project_name
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  depends_on = [
    null_resource.docker_build_push,
    azurerm_postgresql_flexible_server_database.app,
  ]

  # Secret vars
  secret {
    name  = "acr-password"
    value = azurerm_container_registry.acr.admin_password
  }
  secret {
    name  = "db-password"
    value = var.db_password
  }
  secret {
    name  = "openai-key"
    value = var.openai_api_key
  }
  secret {
    name  = "django-secret"
    value = var.django_secret_key
  }
  secret {
    name  = "su-password"
    value = var.django_superuser_password
  }

  registry {
    server               = azurerm_container_registry.acr.login_server
    username             = azurerm_container_registry.acr.admin_username
    password_secret_name = "acr-password"
  }

  template {
    # Ensure container is always running
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "web"
      image  = "${azurerm_container_registry.acr.login_server}/${var.project_name}:${var.docker_image_tag}"
      cpu    = 1.0
      memory = "2Gi"

      env {
        name  = "DB_HOST"
        value = azurerm_postgresql_flexible_server.db.fqdn
      }
      env {
        name  = "DB_PORT"
        value = var.db_port
      }
      env {
        name  = "DB_SSLMODE"
        value = "require"
      }
      env {
        name  = "POSTGRES_DB"
        value = azurerm_postgresql_flexible_server_database.app.name
      }
      env {
        name  = "POSTGRES_USER"
        value = "pgadmin"
      }
      env {
        name        = "POSTGRES_PASSWORD"
        secret_name = "db-password"
      }
      env {
        name        = "OPENAI_API_KEY"
        secret_name = "openai-key"
      }
      env {
        name        = "DJANGO_SECRET_KEY"
        secret_name = "django-secret"
      }
      env {
        name  = "DJANGO_DEBUG"
        value = "0"
      }
      env {
        name  = "NUM_INTERVIEWS"
        value = var.num_interviews
      }
      env {
        name  = "OPENAI_CHAT_MODEL"
        value = var.openai_chat_model
      }
      env {
        name  = "OPENAI_ANALYSIS_MODEL"
        value = var.openai_analysis_model
      }
      env {
        name  = "OPENAI_EMBEDDING_MODEL"
        value = var.openai_embedding_model
      }
      env {
        name  = "NUM_CONCURRENT_INTERVIEWS"
        value = var.num_concurrent_interviews
      }
      env {
        name  = "DJANGO_SUPERUSER_USERNAME"
        value = var.django_superuser_username
      }
      env {
        name        = "DJANGO_SUPERUSER_PASSWORD"
        secret_name = "su-password"
      }
      env {
        name  = "DJANGO_SUPERUSER_EMAIL"
        value = var.django_superuser_email
      }
    }
  }

  # Traffic
  ingress {
    external_enabled = true
    target_port      = 8000
    
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}
