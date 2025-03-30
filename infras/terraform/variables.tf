variable "name" {
  default = "eks-debug-assistant"
}

variable "slack_webhook_url" {
  default = ""
}

variable "slack_channel_name" {
  default = ""
}

variable "opensearch_collection_name" {
  description = "Name for the OpenSearch Serverless collection"
  type        = string
  default     = "vector-col"
}
