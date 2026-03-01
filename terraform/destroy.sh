set -euo pipefail

terraform init
terraform destroy -auto-approve
echo "All resources destroyed."