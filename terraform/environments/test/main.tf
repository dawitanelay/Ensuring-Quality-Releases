provider "azurerm" {
  tenant_id       = "${var.tenant_id}"
  subscription_id = "${var.subscription_id}"
  client_id       = "${var.client_id}"
  client_secret   = "${var.client_secret}"
  features {}
}
terraform {
  backend "azurerm" {
    storage_account_name = "tfstate338119138"
    container_name       = "tfstate"
    key                  = "terraform.tfstate"
    access_key           = "mCysoJf566iZgeHi68z+gV6DmJ/9kVR17htzgq+taZeXMYorFg3BX5e/f5lT9YrbpmFXyNPoMb7k+AStfntDMw=="
  }
}
resource "azurerm_resource_group" "test" {
  name     = "${var.resource_group}"
  location = "${var.location}"
}
# module "resource_group" {
#   source               = "../../modules/resource_group"
#   resource_group       = "${var.resource_group}"
#   location             = "${var.location}"
# }
module "network" {
  source               = "../../modules/network"
  address_space        = "${var.address_space}"
  location             = "${var.location}"
  virtual_network_name = "${var.virtual_network_name}"
  application_type     = "${var.application_type}"
  resource_type        = "NET"
  resource_group       = azurerm_resource_group.test.name
  address_prefix_test  = [var.address_prefix_test]
}

module "nsg-test" {
  source           = "../../modules/networksecuritygroup"
  location         = "${var.location}"
  application_type = "${var.application_type}"
  resource_type    = "NSG"
  resource_group   = azurerm_resource_group.test.name
  subnet_id        = "${module.network.subnet_id_test}"
  address_prefix_test = "${var.address_prefix_test}"
}
module "appservice" {
  source           = "../../modules/appservice"
  location         = "${var.location}"
  application_type = "${var.application_type}"
  resource_type    = "AppService"
  resource_group   = azurerm_resource_group.test.name
}
module "publicip" {
  source           = "../../modules/publicip"
  location         = "${var.location}"
  application_type = "${var.application_type}"
  resource_type    = "publicip"
  resource_group   = azurerm_resource_group.test.name
}

module "vm" {
  source               = "../../modules/vm"
  location             = "${var.location}"
  application_type     = "${var.application_type}"
  resource_type        = "VM"
  resource_group       = azurerm_resource_group.test.name
  subnet_id            = "${module.network.subnet_id_test}"
  public_ip_address_id = "${module.publicip.public_ip_address_id}"
}
