pipeline {
    agent {
        kubernetes {
            yaml """
apiVersion: v1
kind: Pod
metadata:
  labels:
    app: kaniko
spec:
  containers:
    - name: kaniko
      image: gcr.io/kaniko-project/executor:debug
      command:
        - tail
        - "-f"
        - /dev/null
      tty: true
      volumeMounts:
        - name: regcred
          mountPath: /kaniko/.docker/config.json
          subPath: .dockerconfigjson
  volumes:
    - name: regcred
      secret:
        secretName: regcred
"""
        }
    }
    stages {
        environment {
          IMAGE_NAME = 'aaliyah097/bochat'
        }
        stage('Checkout') {
          steps {
            // В Multibranch Pipeline Jenkins сам клонирует репозиторий,
            // но если нужно, можно явно указать checkout:
            checkout scm
          }
        }
        stage('Set Image Tag') {
          steps {
            script {
              // Получаем короткий хэш коммита (7 символов)
              env.IMAGE_TAG = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
              echo "Using commit hash as image tag: ${env.IMAGE_TAG}"
            }
          }
        }
        stage('Build Docker Image with Kaniko') {
          steps {
            container('kaniko') {
              sh '''
              /kaniko/executor \
                --context=`pwd` \
                --dockerfile=Dockerfile \
                --destination=${IMAGE_NAME}:${IMAGE_TAG} \
                --verbosity=debug
              '''
            }
          }
        }
    }
}
