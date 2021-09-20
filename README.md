# buildTools

## Create new image version

Increment `TAG` in `./build-packer-image.sh`.

Merge/Commit to the `master` branch will create `lt-base-windows-dotnet-vXX` image **with** the image family where `vXX` is the TAG.

PR commits will create `lt-base-windows-dotnet-pull-request-XX` image **without** the image family where `XX` is a PR number.

Use `[skip ci]` in a commit message to avoid creating the new image (see [docs](https://cirrus-ci.org/guide/writing-tasks/#conditional-task-execution)). 

## Images

Images are in [Google Cloud Platform](https://console.cloud.google.com/compute/images?organizationId=472937710676&project=language-team). 

The latest image with `lt-base-windows-dotnet` family is used by the build jobs.

### Manual cleanup

We should keep only last 5 versions in GCP. Delete older images manually.

## Before building for your own GCP project

### Create WinRM firewall rule

By default traffic on `tcp:5986` is not allowed so we need to add a firewall rule for a project we want to build images for:

```bash
gcloud compute firewall-rules create default-allow-winrm \
    --project $PROJECT_ID \
    --allow tcp:5986 \
    --priority 65534 \
    --target-tags packer
```


