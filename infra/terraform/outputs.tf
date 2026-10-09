output "server_ip" {
  description = "Public IPv4 address"
  value       = hcloud_server.fbt.ipv4_address
}

output "server_ipv6" {
  description = "Public IPv6 address"
  value       = hcloud_server.fbt.ipv6_address
}

output "ssh_command" {
  description = "SSH command to connect"
  value       = "ssh deploy@${hcloud_server.fbt.ipv4_address}"
}

output "app_dir" {
  description = "Application directory on the server"
  value       = "/opt/fbt"
}