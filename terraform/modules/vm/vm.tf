resource "azurerm_network_interface" "test" {
  name                = "${var.application_type}-nic"
  location            = "${var.location}"
  resource_group_name = "${var.resource_group}"

  ip_configuration {
    name                          = "internal"
    subnet_id                     = "${var.subnet_id}"
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = "${var.public_ip_address_id}"
  }
}

resource "azurerm_linux_virtual_machine" "test" {
  name                =  "${var.application_type}-${var.resource_type}"
  location            = "${var.location}"
  resource_group_name = "${var.resource_group}"
  size                = "Standard_DS2_v2"
  admin_username      = "adminuser"
  network_interface_ids = [azurerm_network_interface.test.id]
  admin_ssh_key {
    username   =  "adminuser"
    public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC7CHHFBsSi2f/Qi8M5Q03fyt2t8YPwJZli3PaJvAJ+uzkt7tDfTCtfr/AMIzEvL/54aqMMoX9TV2Pl25CNChR6mfpsQzy4ZqYeB3s7o3KYXaJjPKpQlDAt1IvCrIskm5rDJRw5pgVEFGqlnJoPT5jSpHvGqbl3/U7DUPyq7iOv8soYYkBx19WH1jYHpzET3w5mXCF1vMAImmeudRW/16xS7gOzqdQtgokWZlrbAXeALvt078XB7ZT3a2KGTsh7G52JyJ4f9zPI+L0kECO5uYY3tjN4+VhSGoFm3GKaYRPhNyCxjn0DMbvTIx/Wp1KarcJuAIQT+qU3Q8yTz39erruilS9l+7svAfJ27HAwJaaHOTcA6xgvEIurvOrFsV0oAgnzvaLx6Ugf69TIQSqHYYgoIgtZf2qUsGyxNE3rRa4pT5UlE7s3eUox7YbzecnE+xtt2nqj/TUQwQT1wouwgHrFJWn+tLzLmIHyJPmUVB1Sn+qPLPDt8AY2FG4B8KQkzA8qfvPuTsFgqz1QRyKw/I5MJ+T2RCIkjnQm7Rgrp7Ig8MROTDhXeXfktZXNd9dxZuwgUMNDjt1+THrwRs25QWwXcS9aE0sPMhV9tstTYtfH1ruKidxw7ZzvvyeKkNGDEzX8RLfiAW9rfvTFPb9/Lcn9czvlUWGv7h4Eh7Bb3y/OUQ== dawitmezemir@gmail.com"
  }
  os_disk {
    caching           = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }
  source_image_reference {
    publisher = "Canonical"
    offer     = "UbuntuServer"
    sku       = "18.04-LTS"
    version   = "latest"
  }
}
