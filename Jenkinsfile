pipeline {
    agent any

    environment {
        // Настройки Docker
        DOCKER_REGISTRY = 'aaliyah097'
        APP_NAME = 'bo-chat'
        DOCKER_CRED = 'docker-credentials'
    }

    stages {
        stage('Checkout') {
            steps {
                // Склонируем репозиторий (укажи свою URL)
                git url: 'https://github.com/Aaliyah097/bochat.git'
            }
        }

        stage('Build & Push Docker') {
            steps {
                script {
                    // Сборка Docker-образа
                    sh """
                    docker build -t \$DOCKER_REGISTRY/\$APP_NAME:\$BUILD_NUMBER .
                    """

                    // Авторизация и пуш в регистр
                    withCredentials([usernamePassword(credentialsId: "${DOCKER_CRED}", usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                        sh """
                        docker login \$DOCKER_REGISTRY -u \$DOCKER_USER -p \$DOCKER_PASS
                        docker push \$DOCKER_REGISTRY/\$APP_NAME:\$BUILD_NUMBER
                        docker logout \$DOCKER_REGISTRY
                        """
                    }
                }
            }
        }

        stage('Deploy to Kubernetes') {
            // Выполняем деплой только если ветка develop или main
            when {
                expression { 
                    env.GIT_BRANCH == 'origin/develop' || env.GIT_BRANCH == 'origin/main'
                }
            }
            steps {
                script {
                    // Определяем окружение на основе ветки
                    def targetEnv = ''
                    def valuesFile = ''
                    
                    if (env.GIT_BRANCH == 'origin/develop') {
                        targetEnv = 'dev'
                        // valuesFile = 'environments/dev/values-dev.yaml'
                    } else if (env.GIT_BRANCH == 'origin/main') {
                        targetEnv = 'prod'
                        // valuesFile = 'environments/prod/values-prod.yaml'
                    }

                    // helm upgrade --install
                    sh """
                    helm upgrade --install bo-chat ./helm \\
                      -n \$targetEnv \\
                      -f \$valuesFile \\
                      --set image.repository=\$DOCKER_REGISTRY/\$APP_NAME \\
                      --set image.tag=\$BUILD_NUMBER
                    """
                }
            }
        }
    }

    post {
        always {
            echo "Pipeline completed."
        }
        success {
            echo "Deployment successful!"
        }
        failure {
            echo "Deployment failed."
        }
    }
}
