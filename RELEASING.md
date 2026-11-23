# Releasing

A release puts the Java library on Maven Central as `io.github.msinghal34:namematch:<version>`.
Releases there are permanent: a version can never be changed or deleted, only followed by a new one.

## Once

1. Sign in at https://central.sonatype.com with the `msinghal34` GitHub account.
   Signing in through GitHub verifies the namespace `io.github.msinghal34` by itself.
2. In the portal, under Account, generate a user token and put it in `~/.m2/settings.xml`:

   ```xml
   <settings>
     <servers>
       <server>
         <id>central</id>
         <username>TOKEN USERNAME</username>
         <password>TOKEN PASSWORD</password>
       </server>
     </servers>
   </settings>
   ```

3. The public half of the signing key (`93FFD296FE381B4DB44519C2238AB63F930CA10F`, named in `java/pom.xml`) must be on a keyserver so Maven Central can check the signatures.
   It is on keyserver.ubuntu.com; a new key goes there with `gpg --keyserver keyserver.ubuntu.com --send-keys <KEY ID>`.

## Each release

1. The version in `python/src/namematch/rules.toml`, `python/pyproject.toml` and `java/pom.xml` is the same, and `python conformance/make_cases.py` has been run.
2. `cd python && python -m pytest`, `cd java && mvn verify`, and `python tools/compare_private.py <real pairs>` all pass.
3. `cd java && JAVA_HOME=<a JDK 17 or newer> mvn -P release deploy` builds, signs and uploads the release; GPG asks for the key's passphrase.
   The classes still target Java 11; the newer JDK is for the javadoc tool, which some Java 11 installs lack.
4. At https://central.sonatype.com under Deployments, check the upload and press Publish.
   It appears on Maven Central within about half an hour.
5. Tag the commit: `git tag v<version> && git push --tags`.
