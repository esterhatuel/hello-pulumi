# S3- Static-Website with CloudFront and BucketNotifictions

This project sets up a public S3 bucket-hosting static website, and bucket notifications which triggered by bucket-notifictions when object created or deleted from the bucket.

The notifictions sent to the SNS-topic subscribes.

In addtion, CloudFront sets behind the s3 bucket to serve HTTPS requests. 




## Architecture: ##
![Alt text](lucid.png?raw=true "Title")



## Created Resources  ##
![Alt text](resourceslist.png?raw=true "Title")

### Prequsties # 

* Pulumi version 3.47.1


