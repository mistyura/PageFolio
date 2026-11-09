grok review failed or returned empty output. stderr:
Couldn't start session: Managed policy could not be verified: the policy lock file under C:\Users\shdwf\.grok is not accessible. Fix permissions and start again.
Error: Couldn't start session: Managed policy could not be verified: the policy lock file under C:\Users\shdwf\.grok is not accessible. Fix permissions and start again.

Diagnosis: grok ran with no effort argument, so the reviewer CLI's own configuration applied and exited with status 1.
