set -euo pipefail

terraform init
terraform apply -auto-approve
echo "Deployment completed."