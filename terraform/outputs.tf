output "app_url" {
  description = "Public URL of the deployed application"
  value       = "https://${azurerm_container_app.web.ingress[0].fqdn}"
}

output "acr_login_server" {
  description = "ACR login server"
  value       = azurerm_container_registry.acr.login_server
}
